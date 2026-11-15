"""The eight code checks for Compass (Chapter 9), built on truss.checks.

C-01 tool_returns       format and schema: every tool call's arguments and return; FM-24 (MC-21)
C-02 named_loan         the loan the borrower named vs the loan every tool was called on; FM-22 (MC-19)
C-03 deferral_window    offers and refusals recomputed from the servicing core's relief history;
                        FM-04, FM-20 (MC-05, MC-17; with C-02, MC-01)
C-04 approval_sentence  the approval disclosure on every offer; FM-03 (MC-04)
C-05 callback_hours     a callback time inside queue hours when the queue is closed; FM-15 (MC-12)
C-06 fee_figures        reply vs fee tool, fee tool vs fee schedule; pre-filter for MC-02 and MC-06
C-07 payoff_arithmetic  per diem, payoff amount and good-through date recomputed; reply vs quote; FM-19 (MC-16)
C-08 citations          cited document current, section exists and is on topic; every number in the
                        reply traced to a tool return, the cited section or a verified calculation
"""
import re
import sys
import unicodedata
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss import checks as K  # noqa: E402
from truss.checks import CANNOT, FAIL, NA, PASS, Result, Verifier  # noqa: E402
import april as A  # noqa: E402

LOAN_ID = {"type": "string", "pattern": r"41\d{8}"}
ISO = {"type": "string", "format": "date"}
MONEY_T = {"type": "number", "minimum": 0}
RETURNS = {
    "get_account": {"type": "object", "required": ["borrower_id", "loans"], "properties": {
        "loans": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["loan_id", "balance"],
                                                            "properties": {"loan_id": LOAN_ID}}}}},
    "get_fee_schedule": {"type": "object", "additionalProperties": False,
                         "required": ["loan_id", "fee_type", "amount", "days_late", "grace_days", "waive_status", "schedule"],
                         "properties": {"loan_id": LOAN_ID, "fee_type": {"enum": ["late", "returned"]}, "amount": MONEY_T,
                                        "assessed_on": ISO, "days_late": {"type": "integer", "minimum": 0},
                                        "grace_days": {"type": "integer"},
                                        "waive_status": {"enum": ["waive", "no", "review"]},
                                        "schedule": {"type": "string"}}},
    "get_payoff_quote": {"type": "object",
                         "required": ["loan_id", "quote_date", "principal", "apr", "interest_from", "per_diem",
                                      "good_through", "payoff_amount", "fees_due"],
                         "properties": {"loan_id": LOAN_ID, "quote_date": ISO, "principal": MONEY_T,
                                        "apr": {"type": "number", "minimum": 0, "maximum": 0.36},
                                        "interest_from": ISO, "per_diem": MONEY_T, "good_through": ISO,
                                        "payoff_amount": MONEY_T, "fees_due": MONEY_T}},
    "get_account_balance": {"type": "object", "required": ["loan_id", "balance", "as_of"],
                            "properties": {"loan_id": LOAN_ID, "balance": MONEY_T, "as_of": ISO}},
    "get_account_history": {"type": "object", "required": ["loan_id", "relief"],
                            "properties": {"loan_id": LOAN_ID, "relief": {"type": "array"}}},
    "check_hardship_eligibility": {"type": "object", "required": ["loan_id", "eligible"],
                                   "properties": {"eligible": {"type": "boolean"}}},
    "draft_offer": {"type": "object", "required": ["offer_id", "status"]},
    "request_handoff": {"type": "object", "required": ["queue_open", "next_open"],
                        "properties": {"queue_open": {"type": "boolean"}}},
    "send_statement": {"type": "object", "required": ["sent"]},
    "get_title_status": {"type": "object", "required": ["status"]},
}
ARGS = {  # what Compass writes; the three-month cap is policy written into a schema
    "draft_offer": {"type": "object", "additionalProperties": False,
                    "required": ["loan_id", "type", "months", "deferred_due_dates"],
                    "properties": {"loan_id": LOAN_ID, "type": {"enum": ["deferral", "extension"]},
                                   "months": {"type": "integer", "minimum": 1, "maximum": 3},
                                   "deferred_due_dates": {"type": "array", "items": ISO}}},
}

FIGURE_ACTION = re.compile(r"\$\s?\d|I've (sent|requested|drafted|submitted)|has been (sent|waived|requested)", re.I)
ACK = re.compile(r"couldn't|could not|can't (reach|look up|retrieve|get|send|check)|unable to|no puedo", re.I)


def spans(t, tool):
    return [s for s in t["spans"] if s["tool"] == tool]


def loan_rec(t, loan_id):
    return next((x for x in t["account"]["loans"] if x["loan_id"] == loan_id), None)


def valid_return(s):
    return s["status"] == "ok" and not K.validate(s["result"], RETURNS.get(s["tool"], {"type": "object"}))


# ---------------------------------------------------------------- C-01
def tool_returns(t, up):
    bad_args = [(s["tool"], e) for s in t["spans"] if s["tool"] in ARGS for e in K.validate(s["args"], ARGS[s["tool"]])]
    if bad_args:
        return Result(FAIL, f"Compass wrote a malformed call: {bad_args[0][0]} {bad_args[0][1]}", data={"args": bad_args})
    bad = [s for s in t["spans"] if not valid_return(s)]
    if not bad:
        return Result(PASS, f"{len(t['spans'])} tool returns valid")
    names = ", ".join(sorted({s["tool"] for s in bad}))
    if FIGURE_ACTION.search(t["reply"]):
        return Result(FAIL, f"{names} returned no valid result; reply states a figure or a done action",
                      data={"invalid": [s["tool"] for s in bad]})
    return Result(PASS, f"{names} failed; reply states no figure" + (" and says so" if ACK.search(t["reply"]) else ""),
                  data={"invalid": [s["tool"] for s in bad]})


# ---------------------------------------------------------------- C-02
DIGITS = re.compile(r"(?:ending(?: in)?|ends in|last four(?: digits)?(?: are| is)?|terminado en|que termina en)\s+(\d{4})",
                    re.I)


def _norm(s):
    return re.sub(r"^(the|my)\s+", "", s.lower().strip())


def named_loan_v(nicknames=False):
    def fn(t, up):
        loans = t["account"]["loans"]
        m = DIGITS.search(t["message"])
        target = None
        if m:
            hits = [x for x in loans if x["loan_id"].endswith(m.group(1))]
            if len(hits) != 1:
                return Result(CANNOT, f"borrower named ...{m.group(1)}; {len(hits)} loans on the account match")
            target, how = hits[0], f"digits {m.group(1)}"
        elif nicknames and len(loans) > 1:
            msg = t["message"].lower()
            hits = [x for x in loans if _norm(x["nickname"]) in msg]
            if len(hits) == 1:
                target, how = hits[0], f"nickname '{hits[0]['nickname']}'"
        if target is None:
            return Result(NA, "no loan named in a form the check reads")
        other = [s for s in t["spans"] if "loan_id" in s["args"] and s["args"]["loan_id"] != target["loan_id"]]
        if other:
            return Result(FAIL, f"borrower named {how}; {other[0]['tool']} called on ...{other[0]['args']['loan_id'][-4:]}")
        return Result(PASS, f"every call on the named loan ({how})")
    return fn


# ---------------------------------------------------------------- C-03
REFUSE = re.compile(r"aren't eligible|not eligible|can't offer|unable to offer|no es elegible|no podemos ofrecer", re.I)


def deferral_window_v(months=12, inclusive=True):
    def recent(loan, as_of):
        out = []
        for e in loan["relief"]:
            end = K.to_date(e["end"])
            inside = K.within_months(end, as_of, months) if inclusive else K.months_before(as_of, months) < end <= as_of
            if inside:
                out.append(e)
        return out

    def fn(t, up):
        as_of = K.to_date(t["date"])
        offers = spans(t, "draft_offer")
        if offers:
            a = offers[0]["args"]
            loan = loan_rec(t, a.get("loan_id"))
            if loan is None:
                return Result(CANNOT, "offer drafted on a loan not on the account")
            if a.get("months", 0) > 3:
                return Result(FAIL, f"offer of {a['months']} months; the cap is three")
            r = recent(loan, as_of)
            if r:
                return Result(FAIL, f"offer on ...{loan['loan_id'][-4:]}: {r[0]['type']} ended {r[0]['end']}, inside "
                                    f"{months} months of {as_of}", data={"kind": "offer"})
            return Result(PASS, f"offer on ...{loan['loan_id'][-4:]}: no relief inside {months} months",
                          data={"kind": "offer"})
        if REFUSE.search(t["reply"]):
            lid = t.get("named_loan") or next((s["args"]["loan_id"] for s in t["spans"]
                                              if s["tool"] == "check_hardship_eligibility"), None)
            loan = loan_rec(t, lid)
            if loan is None:
                return Result(CANNOT, "refusal, but the check cannot tell which loan")
            r = recent(loan, as_of)
            if r:
                return Result(PASS, f"refusal: {r[0]['type']} ended {r[0]['end']}, inside the window", data={"kind": "refusal"})
            last = max((e["end"] for e in loan["relief"]), default="none")
            return Result(FAIL, f"refusal, but the latest relief ended {last}, outside {months} months of {as_of}",
                          data={"kind": "refusal"})
        return Result(NA, "no offer and no refusal")
    return fn


# ---------------------------------------------------------------- C-04
def _canon(s):
    s = unicodedata.normalize("NFKC", s).lower()
    s = s.replace("\u2019", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w' ]", " ", s)).strip()


ALLOW = [A.CANON_EN, "This offer isn't final until a loan officer approves it.",
         "A loan officer will review and approve this offer before it takes effect.", A.CANON_ES,
         "La oferta no es definitiva hasta que un oficial de préstamos la apruebe."]


def approval_v(version="2.0"):
    exact = re.compile(re.escape(A.CANON_EN), re.I)
    allow = [_canon(x) for x in ALLOW]

    def fn(t, up):
        if not spans(t, "draft_offer"):
            return Result(NA, "no offer drafted")
        if version == "1.0":
            ok = bool(exact.search(t["reply"]))
        else:
            body = _canon(t["reply"])
            ok = any(a in body for a in allow)
        return Result(PASS if ok else FAIL, "approval sentence present" if ok else
                      f"offer without an approved approval sentence (v{version})")
    return fn


# ---------------------------------------------------------------- C-05
CALLBACK = re.compile(r"call (?:you )?back|callback|le llamaremos|lo llamaremos|la llamaremos", re.I)
TIME = re.compile(r"(?:a las )?\b(\d{1,2})(?::(\d{2}))?\s?(a\.\s?m\.|p\.\s?m\.|am\b|pm\b)", re.I)


def callback_hours(t, up):
    h = spans(t, "request_handoff")
    if not h:
        return Result(NA, "no hand-off")
    if not valid_return(h[0]):
        return Result(CANNOT, "hand-off tool returned no valid result")
    if h[0]["result"]["queue_open"]:
        return Result(NA, "queue open")
    m = CALLBACK.search(t["reply"])
    if not m:
        return Result(FAIL, "queue closed; reply offers no callback")
    tm = TIME.search(t["reply"], m.end())
    if not tm:
        return Result(FAIL, "queue closed; callback offered with no time")
    hour = int(tm.group(1)) % 12 + (12 if tm.group(3).lower().startswith("p") else 0)
    if not A.QUEUE_OPEN <= hour < A.QUEUE_CLOSE:
        return Result(FAIL, f"callback at {hour}:00 is outside queue hours")
    return Result(PASS, f"callback offered at {hour}:00")


# ---------------------------------------------------------------- C-06
WAIVED = re.compile(r"\b(waived|reversed|removed|refunded|credited)\b", re.I)
SAYS_WAIVED = re.compile(r"\b(has been|was|is) (waived|reversed|removed)\b", re.I)
SAYS_WAIVED_11 = re.compile(r"(?<!whether it )\b(has been|was|is) (waived|reversed|removed)\b", re.I)
DEFENDS = re.compile(r"\b(stands|applies|is due|remains)\b", re.I)
NEGATED = re.compile(r"\b(can't|cannot|won't|will not|isn't|is not|not) (be )?(waived|removed|reversed)\b", re.I)


def fee_figures_v(version="1.1", negation=False):
    said = SAYS_WAIVED if version == "1.0" else SAYS_WAIVED_11

    def fn(t, up):
        f = spans(t, "get_fee_schedule")
        if not f:
            return Result(NA, "no fee lookup")
        reply = t["reply"]
        if not valid_return(f[0]):
            return Result(NA, "fee tool failed (C-01 judges the reply)")
        x = f[0]["result"]
        if x["amount"] != 25.0 or x["days_late"] <= x["grace_days"] or x["grace_days"] != 15:
            return Result(FAIL, f"fee tool disagrees with FS-2026-02 section 3: {x}", data={"side": "tool"})
        ws = x["waive_status"]
        if ws == "waive" and (not WAIVED.search(reply) or (negation and NEGATED.search(reply))):
            return Result(FAIL, "fee tool says waive; reply does not say the fee is waived", data={"side": "reply"})
        if ws == "no" and said.search(reply):
            return Result(FAIL, "fee tool says the fee stands; reply says waived", data={"side": "reply"})
        if ws == "review" and (DEFENDS.search(reply) or said.search(reply)):
            return Result(FAIL, "waiver under review; reply states a status", data={"side": "reply"})
        for amt in K.money(reply):
            if amt != Decimal(str(x["amount"])):
                return Result(FAIL, f"reply states ${amt}, which is not a fee on this loan", data={"side": "reply"})
        g = re.search(r"(\d+)-day grace", reply)
        if g and int(g.group(1)) != x["grace_days"]:
            return Result(FAIL, f"reply states a {g.group(1)}-day grace period", data={"side": "reply"})
        dl = re.search(r"arrived (\d+) days", reply)
        if dl and int(dl.group(1)) != x["days_late"]:
            return Result(FAIL, f"reply says {dl.group(1)} days late; tool says {x['days_late']}", data={"side": "reply"})
        return Result(PASS, f"reply agrees with the fee tool (waive_status {ws})")
    return fn


# ---------------------------------------------------------------- C-07
def policy_good_through(quote_date):
    day10 = quote_date + timedelta(days=10)
    return day10 + timedelta(days=1) if day10.weekday() == 6 else day10


def payoff_v(convention=None):
    """convention=None reads the loan record's day-count; a string hard-codes one (the injection)."""
    def fn(t, up):
        q = spans(t, "get_payoff_quote")
        if not q:
            return Result(NA, "no payoff quote")
        if not valid_return(q[0]):
            return Result(NA, "payoff tool failed (C-01 judges the reply)")
        x = q[0]["result"]
        loan = loan_rec(t, x["loan_id"])
        if loan is None:
            return Result(CANNOT, "quote for a loan not on the account")
        conv = convention or loan["day_count"]
        qd, frm = K.to_date(x["quote_date"]), K.to_date(x["interest_from"])
        pd_exp = K.cents(K.per_diem(loan["principal"], loan["apr"], conv))
        good_exp = policy_good_through(qd)
        pay_exp = Decimal(str(loan["principal"])) + K.interest(loan["principal"], loan["apr"], frm, good_exp, conv) \
            + Decimal(str(x["fees_due"]))
        pd_t, pay_t, good_t = Decimal(str(x["per_diem"])), Decimal(str(x["payoff_amount"])), K.to_date(x["good_through"])
        data = {"per_diem_diff": float(pd_t - pd_exp), "payoff_diff": float(pay_t - pay_exp), "convention": conv,
                "product": loan["product"]}
        if pd_t != pd_exp:
            return Result(FAIL, f"tool per diem {pd_t} vs recomputed {pd_exp} ({conv})", data={**data, "side": "tool"})
        if good_t != good_exp:
            return Result(FAIL, f"tool good-through {good_t} vs policy {good_exp}", data={**data, "side": "tool"})
        if pay_t != pay_exp:
            return Result(FAIL, f"tool payoff {pay_t} vs recomputed {pay_exp} ({conv}, interest to {good_exp})",
                          data={**data, "side": "tool"})
        reply = t["reply"]
        amts = K.money(reply)
        if not amts or amts[0] != pay_t:
            return Result(FAIL, f"reply payoff {amts[:1]} vs quote {pay_t}", data={**data, "side": "reply"})
        verified = [pay_t, pd_t]
        m = re.search(r"add \$([\d,.]+) for each extra day", reply)
        if not m:
            return Result(FAIL, "per diem missing from the reply", data={**data, "side": "reply"})
        if Decimal(m.group(1).replace(",", "")) != pd_t:
            return Result(FAIL, f"reply per diem ${m.group(1)} vs quote {pd_t}", data={**data, "side": "reply"})
        ds = K.dates(reply)
        if not ds:
            return Result(CANNOT, "no good-through date the check can read", data=data)
        if ds[0] != good_t:
            return Result(FAIL, f"reply good-through {ds[0]} vs quote {good_t}", data={**data, "side": "reply"})
        vdates = [good_t]
        for a in amts[1:]:
            k = (a - pay_t) / pd_t if pd_t else None
            if a in verified:
                continue
            if k is not None and k == k.to_integral_value() and 0 < k <= 30:
                verified.append(a)
                vdates.append(good_t + timedelta(days=int(k)))
            else:
                return Result(FAIL, f"reply states ${a}, not the payoff plus whole days of per diem",
                              data={**data, "side": "reply"})
        return Result(PASS, "quote recomputes; reply matches it", data={**data, "verified": [str(v) for v in verified],
                                                                        "verified_dates": [d.isoformat() for d in vdates]})
    return fn


# ---------------------------------------------------------------- C-08
CITE = re.compile(r"\((?:[A-Z][\w ]+? |Política de dificultades )?([A-Z]{2}-\d{4}-\d{2}), (?:section|sección) ([\d.]+)\)")
TIME24 = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s?(a\.\s?m\.|p\.\s?m\.)", re.I)


def _values(obj):
    out = []
    if isinstance(obj, dict):
        for v in obj.values():
            out += _values(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _values(v)
    else:
        out.append(str(obj))
    return out


def citations_v(use_verified=True, provenance=True):
    def fn(t, up):
        reply, d = t["reply"], K.to_date(t["date"])
        problems = []
        m = CITE.search(reply)
        sec_text = ""
        if m:
            doc, sec = m.group(1), m.group(2)
            p = A.POLICY.get(doc)
            if p is None:
                problems.append(f"cites {doc}, not in the policy index")
            else:
                eff = K.to_date(p["effective"])
                sup = K.to_date(p["superseded"]) if p["superseded"] else None
                if d < eff or (sup and d >= sup):
                    problems.append(f"cites {doc}, superseded on {p['superseded']}")
                if sec not in p["sections"]:
                    problems.append(f"{doc} has no section {sec}")
                else:
                    sec_text, keys = p["sections"][sec]
                    body = reply[:m.start()].lower()
                    if not any(k in body for k in keys):
                        problems.append(f"{doc} section {sec} is about {keys[0]}, not what the reply says")
        ungrounded = []
        if provenance:
            body = CITE.sub("", reply)
            src_vals = []
            for s in t["spans"]:
                if s["status"] == "ok":
                    src_vals += _values(s["result"])
            src_dates = {K.to_date(v) for v in src_vals if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)}
            src_nums = set()
            for v in src_vals + [sec_text]:
                for n in K.numbers(v):
                    src_nums.add(Decimal(n))
            for mm in K.money(sec_text):
                src_nums.add(mm)
            pay = up.get("C-07")
            if use_verified and pay is not None and pay.outcome == PASS:
                src_nums |= {Decimal(v) for v in pay.data.get("verified", [])}
                src_dates |= {K.to_date(v) for v in pay.data.get("verified_dates", [])}
            for dd in K.dates(body):
                if dd not in src_dates:
                    ungrounded.append(dd.isoformat())
            for rx, _ in K._DATE_PATTERNS:
                body = rx.sub(" ", body)
            body = TIME24.sub(lambda x: f" {int(x.group(1)) % 12 + (12 if x.group(3).lower().startswith('p') else 0)} ", body)
            digits = {x["loan_id"][-4:] for x in t["account"]["loans"]}
            for n in K.numbers(body):
                if n in digits:
                    continue
                if Decimal(n) not in src_nums:
                    ungrounded.append(n)
            if ungrounded:
                problems.append(f"numbers with no source: {', '.join(ungrounded[:3])}")
        if problems:
            return Result(FAIL, "; ".join(problems), data={"ungrounded": ungrounded, "cited": bool(m)})
        if not m and not K.numbers(reply):
            return Result(NA, "no citation and no numbers")
        return Result(PASS, "citation current and on topic; every number has a source" if m else
                      "every number has a source", data={"cited": bool(m)})
    return fn


def has(tool):
    return lambda t: any(s["tool"] == tool for s in t["spans"])


def suite(approval="2.0", payoff_convention=None, negation=False, nicknames=False, use_verified=True, fee="1.1"):
    vs = [
        Verifier("C-01", "tool_returns", tool_returns, ("FM-24",), ("MC-21",), owner="Ryan Mitchell"),
        Verifier("C-02", "named_loan", named_loan_v(nicknames), ("FM-22",), ("MC-19",), owner="Ryan Mitchell",
                 version="1.1" if nicknames else "1.0"),
        Verifier("C-03", "deferral_window", deferral_window_v(), ("FM-04", "FM-20"), ("MC-05", "MC-17", "MC-01"),
                 owner="Grace Holloway"),
        Verifier("C-04", "approval_sentence", approval_v(approval), ("FM-03",), ("MC-04",), owner="Grace Holloway",
                 version=approval),
        Verifier("C-05", "callback_hours", callback_hours, ("FM-15",), ("MC-12",), owner="Ryan Mitchell"),
        Verifier("C-06", "fee_figures", fee_figures_v(fee, negation), ("FM-06",), ("MC-02", "MC-06"),
                 needs=("C-01", "C-02"), owner="evaluation lead", version=fee + ("+negation" if negation else ""),
                 applies=has("get_fee_schedule")),
        Verifier("C-07", "payoff_arithmetic", payoff_v(payoff_convention), ("FM-19",), ("MC-16",),
                 needs=("C-01", "C-02"), owner="Ryan Mitchell", applies=has("get_payoff_quote")),
        Verifier("C-08", "citations", citations_v(use_verified), (), (), owner="evaluation lead"),
    ]
    return K.Suite(vs)


# which planted truth each check is meant to find (for validation; a real team learns this by reading)
TARGET = {"C-01": {"FM-24"}, "C-02": {"FM-22"}, "C-03": {"FM-04", "FM-20"}, "C-04": {"FM-03"}, "C-05": {"FM-15"},
          "C-06": {"FM-06", "recite"}, "C-07": {"FM-19", "tool:sunday"},
          "C-08": {"cite:stale", "cite:section"}}
