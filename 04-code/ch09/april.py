"""Chapter 9 fixture: Compass conversations from Thu 1 to Wed 14 April 2027, rendered as traces
with text, so code checks have something real to read.

Frame: Chapter 7's generator (seed 2028), IDs continuing at t-100099 (the fixture generates the first
fortnight of each month only, as in February and March). Release in production: rc-0326-2 (since
Mon 29 Mar at 10% traffic): it applies the fee tool's waiver field about 85% of the time; the
wrapper bug (FM-22 by digits, FM-24) is still live until Ryan's fix ships.

render(row, release) turns a generator row into a trace: the servicing core's account snapshot
(loans, products, day-count conventions, relief history), the borrower's first message, the tool
spans (arguments, status, result; a failed call returns {} as the wrapper does), Compass's reply
and its citation. Every choice is seeded by trace ID, so any subset renders the same way.

Planted, and stated in the chapter (a real team sees none of this):
  * nickname wrong-loan cases (borrower says "the Tacoma"; Compass resolves to the other loan)
  * approval sentence wordings: canonical, two acceptable paraphrases, one Victor rules out, Spanish
  * FM-06 replies in three phrasings, two of which use the word "waived" or "removed" in a negation
  * a payoff tool defect: when day ten falls on a Sunday the good-through date rolls to Monday but
    interest is counted only to Sunday (payoff short by one day of interest)
  * the hardship policy renumbering (HP-2027-04 replaces HP-2026-09 on 1 April 2027); some replies
    cite the superseded document or the old section number
  * small-business loans accrue actual/360; auto and personal loans actual/365
`truth` on each trace records what was planted.
"""
import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
sys.path.insert(0, str(HERE.parents[0] / "ch08"))
import february as FEB  # noqa: E402
import march as MAR  # noqa: E402
import compass_sim as C  # noqa: E402
from truss.checks import cents, interest, per_diem  # noqa: E402

FIRST_ID = 100099
DAYS = [date(2027, 4, 1) + timedelta(d) for d in range(14)]
SEED = 2028
QUEUE_OPEN, QUEUE_CLOSE = 8, 19          # hand-off queue staffed 08:00-19:00 Phoenix time
SPANISH = .09                            # hardship conversations held in Spanish
NICKNAME = .30                           # two-loan borrowers in loan flows who name the loan by nickname
NICK_WRONG = .12                         # of those, Compass resolves the nickname to the other loan
FM15_RATE = .04                          # out-of-hours hand-offs whose reply offers no callback time
CITE_STALE = .30                         # April hardship citations copying the old example (HP-2026-09 4.2)
CITE_OLDSEC = .10                        # citing the new document with the old section number
DERIVED = .06                            # correct payoff replies that add a worked "if you pay on" figure
RELEASES = ("production", "rc-0322-1", "rc-0326-2", "rc-0412-1", "rc-0414-2")

CANON_EN = "A loan officer must approve this offer before it takes effect."
APPROVAL_EN = [(CANON_EN, .78, "canonical"),
               ("This offer isn't final until a loan officer approves it.", .12, "para-A"),
               ("A loan officer will review and approve this offer before it takes effect.", .06, "para-B"),
               ("Once a loan officer signs off, your deferral will start.", .04, "para-C")]
CANON_ES = "Un oficial de préstamos debe aprobar esta oferta antes de que entre en vigor."
APPROVAL_ES = [(CANON_ES, .85, "es-canonical"),
               ("La oferta no es definitiva hasta que un oficial de préstamos la apruebe.", .15, "es-para")]
CARS = ["Tacoma", "RAV4", "Civic", "F-150", "Camry", "Outback", "Silverado", "CR-V", "Model 3", "Tundra"]

# ---- the policy index on the conversation date (doc, title, effective, superseded, sections)
POLICY = {
    "FS-2026-02": {"title": "Fee schedule", "effective": "2026-03-01", "superseded": None, "sections": {
        "3": ("A late fee of $25 applies when a payment is received more than 15 days after its due date.",
              ("late fee", "grace")),
        "4": ("A late fee is waived when the borrower has made the previous twelve payments on time, or when "
              "a loan officer approves a courtesy waiver.", ("waive", "waived", "waiver")),
        "5": ("A returned-payment fee of $15 applies when a payment is returned unpaid.", ("returned",)),
        "6": ("No fee is charged for a payoff letter or a lien release.", ("payoff", "lien"))}},
    "HP-2026-09": {"title": "Hardship policy", "effective": "2026-09-01", "superseded": "2027-04-01", "sections": {
        "4.1": ("A borrower facing a hardship may be offered a deferral or a payment extension.", ("hardship",)),
        "4.2": ("A borrower may receive one deferral, of up to three months, in any twelve-month period.",
                ("deferral", "twelve months", "12 months", "aplazamiento", "doce meses"))}},
    "HP-2027-04": {"title": "Hardship policy", "effective": "2027-04-01", "superseded": None, "sections": {
        "4.1": ("A borrower facing a hardship may be offered a deferral or a payment extension.", ("hardship",)),
        "4.2": ("Before any offer, the borrower's monthly income and essential expenses must be confirmed.",
                ("income", "expenses", "ingreso", "gastos")),
        "4.3": ("A borrower may receive one deferral, of up to three months, in any twelve-month period. A payment "
                "extension counts only if it ended within the twelve months before the request.",
                ("deferral", "twelve months", "12 months", "extension", "aplazamiento", "doce meses", "prórroga")),
        "4.4": ("Every hardship offer must be approved by a loan officer before it takes effect, and the offer "
                "must say so.", ("approve", "approved", "loan officer"))}},
    "PL-2026-01": {"title": "Payoff letter policy", "effective": "2026-01-01", "superseded": None, "sections": {
        "2": ("A payoff quote is good through ten calendar days after the quote date; when that day is a Sunday, "
              "through the following Monday, with interest counted to that day.", ("good through", "payoff"))}},
}


def build(seed=SEED):
    saved = FEB.FIRST_ID, FEB.DAYS
    FEB.FIRST_ID, FEB.DAYS = FIRST_ID, DAYS
    try:
        rows = FEB.build(seed)
    finally:
        FEB.FIRST_ID, FEB.DAYS = saved
    for r in rows:
        g = random.Random(f"apr-{r['trace_id']}")
        r["nickname"] = False
        if (r["two_loans"] and not r["named_by_digits"] and r["flow"] in FEB.LOAN_FLOWS
                and g.random() < NICKNAME):
            r["nickname"] = True
            if r["cause"] is None and not r["tool_error"] and g.random() < NICK_WRONG:
                r["cause"] = "X_nickname"
        if r["flow"] == "fee_explanation":
            MAR.enrich(r)
            if r["cause"] == "X_nickname":
                r["wrong_fee"], r["waive_status"], r["deferred"] = True, "no", False
    return rows


# ---------------------------------------------------------------- the servicing core's account
def _loan(g, product=None):
    product = product or g.choices(["auto", "personal", "small_business"], [.80, .14, .06])[0]
    lo, hi = {"auto": (6000, 34000), "personal": (2000, 15000), "small_business": (15000, 60000)}[product]
    alo, ahi = {"auto": (59, 129), "personal": (99, 179), "small_business": (85, 135)}[product]
    principal = cents(Decimal(g.randint(lo * 100, hi * 100)) / 100)
    apr = Decimal(g.randint(alo, ahi)) / 1000
    term = g.choice([36, 48, 60, 72])
    pay = cents(principal * (apr / 12) / (1 - (1 + apr / 12) ** -term))
    nick = {"auto": "the " + g.choice(CARS), "personal": "my personal loan",
            "small_business": "the business loan"}[product]
    return {"loan_id": "41" + "".join(str(g.randint(0, 9)) for _ in range(8)), "product": product,
            "nickname": nick, "principal": principal, "apr": apr, "scheduled_payment": pay,
            "day_count": "actual/360" if product == "small_business" else "actual/365", "relief": []}


def _months_ago(d, lo, hi, g):
    return d - timedelta(days=g.randint(int(lo * 30.4), int(hi * 30.4)))


def account(r, g, conv_date):
    n = 2 if (r.get("two_loans") or r["cause"] in ("X_wrongloan", "X_nickname")) else 1
    loans = [_loan(g)]
    while len(loans) < n:
        x = _loan(g)
        if x["loan_id"][-4:] != loans[0]["loan_id"][-4:] and x["nickname"] != loans[0]["nickname"]:
            loans.append(x)
    if r["trace_id"] in SAGUARO:
        loans[0] = _loan(g, "small_business")
        loans[0]["nickname"] = "the coffee roaster loan"
    for x in loans:
        if g.random() < .15:                                   # old relief, long outside the window
            end = _months_ago(conv_date, 14, 40, g)
            x["relief"].append({"type": g.choice(["deferral", "extension"]), "start": (end - timedelta(60)).isoformat(),
                                "end": end.isoformat()})
    holder = "Saguaro Coffee Roasters LLC" if r["trace_id"] in SAGUARO else None
    return {"borrower_id": "B" + "".join(str(g.randint(0, 9)) for _ in range(7)), "holder": holder, "loans": loans}


SAGUARO = set()   # filled by lab code that wants the named small-business borrower in a frame


# ---------------------------------------------------------------- helpers
def fmt_date(d, style="us"):
    if style == "num":
        return f"{d.month:02d}/{d.day:02d}/{d.year}"
    if style == "es":
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                 "octubre", "noviembre", "diciembre"]
        return f"{d.day} de {meses[d.month - 1]} de {d.year}"
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def usd(x):
    return f"${Decimal(x):,.2f}"


def pick(g, options):
    u, acc = g.random(), 0.0
    for text, p, tag in options:
        acc += p
        if u < acc:
            return text, tag
    return options[-1][0], options[-1][2]


def span(tool, args, result, ok=True):
    return {"tool": tool, "args": args, "status": "ok" if ok else "error", "result": result if ok else {}}


def payoff_quote(loan, quote_date, g, buggy=True):
    """The payoff tool. Defect (planted): Sunday roll moves the date, not the interest."""
    interest_from = quote_date - timedelta(days=g.randint(3, 30))
    day10 = quote_date + timedelta(days=10)
    good = day10 + timedelta(days=1) if day10.weekday() == 6 else day10
    to = day10 if buggy else good
    acc = interest(loan["principal"], loan["apr"], interest_from, to, loan["day_count"])
    return {"loan_id": loan["loan_id"], "quote_date": quote_date.isoformat(), "principal": float(loan["principal"]),
            "apr": float(loan["apr"]), "day_count": loan["day_count"], "interest_from": interest_from.isoformat(),
            "per_diem": float(cents(per_diem(loan["principal"], loan["apr"], loan["day_count"]))),
            "good_through": good.isoformat(), "fees_due": 0.0,
            "payoff_amount": float(loan["principal"] + acc)}


def cite(gc, doc, sec, lang="en"):
    title = POLICY[doc]["title"]
    if lang == "es":
        return f" (Política de dificultades {doc}, sección {sec})"
    return f" ({title} {doc}, section {sec})"


# ---------------------------------------------------------------- render
def render(r, release="rc-0326-2", gate=False):
    """One trace. release selects Compass's behaviour; gate=True means a gate replay (tools do not fail
    unless the case was built to make them fail)."""
    tid = r["trace_id"]
    g = random.Random(f"render-{tid}")
    gc = random.Random(f"cite-{tid}")  # citation choice independent of the release
    started = datetime.fromisoformat(r["started_at"]) if r.get("started_at") else datetime(2026, 10, 1, 11, 0)
    d = started.date()
    acct = account(r, g, d)
    loans = acct["loans"]
    flow = r["flow"]
    cause = r["cause"]
    wrapper_fixed = release in ("rc-0412-1", "rc-0414-2")
    if wrapper_fixed and cause in ("X_wrongloan", "X_invent"):
        cause = None
    lang = "es" if flow == "hardship" and g.random() < SPANISH else "en"
    truth = set()
    named = None
    msg_ref = ""
    if len(loans) == 2 and r.get("named_by_digits"):
        named = loans[1] if r["cause"] == "X_wrongloan" else loans[g.randint(0, 1)]
        msg_ref = (f" on my loan ending {named['loan_id'][-4:]}" if lang == "en"
                   else f" de mi préstamo terminado en {named['loan_id'][-4:]}")
    elif len(loans) == 2 and r.get("nickname"):
        named = loans[g.randint(0, 1)]
        msg_ref = f" on {named['nickname']}" if lang == "en" else f" de {named['nickname']}"
    elif len(loans) == 1:
        named = loans[0]
    used = named or loans[0]
    if cause == "X_wrongloan":
        used = loans[0] if named is loans[1] else loans[1]
    if cause == "X_nickname":
        used = loans[1] if named is loans[0] else loans[0]
    if used is not named and named is not None:
        truth.add("FM-22")
    l4 = (named or used)["loan_id"][-4:]
    spans = [span("get_account", {"borrower_id": acct["borrower_id"]},
                  {"borrower_id": acct["borrower_id"],
                   "loans": [{"loan_id": x["loan_id"], "product": x["product"], "nickname": x["nickname"],
                              "balance": float(x["principal"]), "as_of": d.isoformat(),
                              "scheduled_payment": float(x["scheduled_payment"])} for x in loans]})]
    terr = bool(r.get("tool_error")) and not (gate and not r.get("gate_tool_error"))
    if gate and r.get("gate_tool_error"):
        terr = True
    reply, citation, offer, quote = "", "", None, None
    meta = {"lang": lang, "release": release, "approval": None, "fee_phrase": None}

    if flow == "fee_explanation":
        msg = f"Why was I charged a late fee{msg_ref}?"
        out = r.get("_outcome") or (C.reply(r, release if release in C.RC else "rc-0326-2") if "_u_cand" in r else
                                    {"outcome": "pass", "cause": None})
        oc, ocause = out["outcome"], out["cause"]
        if wrapper_fixed and ocause in ("X_wrongloan", "X_invent"):
            oc, ocause = ("deferred" if ocause == "X_invent" else "pass"), None
        days_late = g.randint(16, 40)
        ws = r.get("waive_status", "no")
        if ocause == "F_waive":
            ws = "waive"
        fee = {"loan_id": used["loan_id"], "fee_type": "late", "amount": 25.0, "assessed_on":
               (d - timedelta(days=g.randint(2, 20))).isoformat(), "days_late": days_late, "grace_days": 15,
               "waive_status": ws, "schedule": "FS-2026-02"}
        fee_err = terr or ocause == "X_invent"
        spans.append(span("get_fee_schedule", {"loan_id": used["loan_id"]}, fee, ok=not fee_err))
        c3 = g.random() < .6
        if ocause == "X_invent":
            reply = "The late fee is $25.00. It was assessed because the payment arrived after the 15-day grace period."
            truth.add("FM-24")
        elif fee_err:
            reply = ("I couldn't retrieve the fee details just now, so a loan officer will follow up to confirm "
                     "the fee and any waiver.")
            c3 = False
        elif oc == "deferred" and ws == "review":
            reply = ("There's an open waiver request on this fee. A loan officer will confirm whether it is waived "
                     "within two business days.")
            c3 = False
        elif oc == "deferred":
            reply = "A loan officer will confirm the fee and whether it can be waived within two business days."
            c3 = False
        elif ocause == "F_waive":
            truth.add("FM-06")
            v = g.random()
            if v < .5:
                reply = (f"The {usd(25)} late fee on your loan ending {l4} stands: your payment arrived {days_late} "
                         f"days after the due date, past the 15-day grace period.")
                meta["fee_phrase"] = "defend"
            elif v < .8:
                reply = (f"I'm sorry, but this late fee can't be waived: your payment arrived {days_late} days after "
                         f"the due date, past the 15-day grace period.")
                meta["fee_phrase"] = "negated-waived"
            else:
                reply = ("The late fee applies because the payment arrived after the 15-day grace period, so it won't "
                         "be removed.")
                meta["fee_phrase"] = "negated-removed"
        elif ws == "waive":
            reply = (f"Good news: the {usd(25)} late fee on your loan ending {l4} has been waived, and the reversal "
                     f"will show on your next statement.")
            c3 = False
            citation = cite(gc, "FS-2026-02", "4") if gc.random() < .6 else ""
        else:
            if g.random() < .25:
                reply = (f"The {usd(25)} late fee on your loan ending {l4} applies, and it can't be waived this time: "
                         f"your payment arrived {days_late} days after the due date, past the 15-day grace period.")
            else:
                reply = (f"The {usd(25)} late fee on your loan ending {l4} applies: your payment arrived {days_late} "
                         f"days after the due date, past the 15-day grace period.")
        if ocause == "recite":
            reply += " Your fee schedule also includes a $15 returned-payment fee, and payoff letters are free."
            truth.add("recite")
        if c3 and not citation:
            citation = cite(gc, "FS-2026-02", "3")
        if ocause == "X_wrongloan" or (cause == "X_nickname"):
            pass
        meta["outcome"] = oc
        meta["wrong_fee"] = bool(truth & {"FM-06", "FM-22", "FM-24", "recite"})

    elif flow == "payoff_letter":
        msg = f"Can I get a payoff quote{msg_ref}?"
        quote = payoff_quote(used, d, g)
        if quote["good_through"] != (d + timedelta(days=10)).isoformat() and not terr:
            truth.add("tool:sunday")
        spans.append(span("get_payoff_quote", {"loan_id": used["loan_id"], "quote_date": d.isoformat()}, quote,
                          ok=not terr))
        good = date.fromisoformat(quote["good_through"])
        style = "num" if g.random() < .2 else "us"
        pd, amt = Decimal(str(quote["per_diem"])), Decimal(str(quote["payoff_amount"]))
        if cause == "X_invent":
            fake = cents(Decimal(str(used["principal"])) * Decimal("1.004"))
            reply = f"Your payoff amount is {usd(fake)}, good through {fmt_date(d + timedelta(days=10), style)}."
            truth.add("FM-24")
        elif terr:
            reply = ("I couldn't get a payoff quote from our system just now. You can request one at "
                     "harborlending.com, or I can try again in a few minutes.")
        else:
            gd, pdx, tail = good, pd, True
            if cause == "P_perdiem":
                truth.add("FM-19")
                if g.random() < .5:
                    tail = False
                else:
                    pdx = cents(Decimal(str(used["principal"])) * Decimal(str(used["apr"])) / 12 / 30)
                    if pdx == pd:
                        pdx = pd + Decimal("0.07")
            elif cause == "P_goodthru":
                truth.add("FM-19")
                gd = good - timedelta(days=g.randint(1, 3))
            reply = f"Your payoff amount for the loan ending {l4} is {usd(amt)}, good through {fmt_date(gd, style)}."
            if tail:
                reply += f" If you pay after that date, add {usd(pdx)} for each extra day."
            if cause is None and g.random() < DERIVED:
                k = 2
                reply += (f" Paying on {fmt_date(good + timedelta(days=k), style)} would make it "
                          f"{usd(amt + k * pd)}.")
                meta["derived"] = True
            citation = cite(gc, "PL-2026-01", "2") if gc.random() < .3 else ""

    elif flow == "account_question":
        msg = f"What's my balance{msg_ref}?"
        spans.append(span("get_account_balance", {"loan_id": used["loan_id"]},
                          {"loan_id": used["loan_id"], "balance": float(used["principal"]), "as_of": d.isoformat()},
                          ok=not terr))
        if cause == "X_invent":
            reply = f"The balance on your loan is {usd(cents(used['principal'] * Decimal('1.01')))}."
            truth.add("FM-24")
        elif terr:
            reply = "I can't reach the account system right now. Please try again in a few minutes."
        else:
            asof = d - timedelta(days=g.randint(3, 20)) if cause == "A_date" else d
            if cause == "A_date":
                truth.add("FM-07")
            reply = (f"The balance on your loan ending {l4} is {usd(used['principal'])} as of "
                     f"{fmt_date(asof)}.")

    elif flow == "hardship":
        msg = ("I lost hours at work and can't make my payment" + msg_ref + "." if lang == "en" else
               "Perdí horas en el trabajo y no puedo hacer mi pago" + msg_ref + ".")
        hist_loan = used
        offer_flag = r.get("offer_drafted", False)
        refusal = False
        # relief history on the loans, by case
        if cause == "X_wrongloan" and r.get("offered_loan_recent_deferral"):
            end = _months_ago(d, 1, 11, g)
            used["relief"].append({"type": "deferral", "start": (end - timedelta(60)).isoformat(), "end": end.isoformat()})
        elif cause == "H_refused":
            end = _months_ago(d, 13, 24, g)
            named_l = named or used
            named_l["relief"] = [{"type": "extension", "start": (end - timedelta(30)).isoformat(), "end": end.isoformat()}]
            refusal = True
            truth.add("FM-20")
        elif cause is None and not offer_flag and g.random() < .35:
            u = g.random()
            if u < .06:
                end = d.replace(year=d.year - 1)                     # exactly twelve months: inside (Grace)
            else:
                end = _months_ago(d, 1, 11, g)
            (named or used)["relief"] = [{"type": g.choice(["deferral", "extension"]),
                                          "start": (end - timedelta(60)).isoformat(), "end": end.isoformat()}]
            refusal = True
        elif cause is None and offer_flag and g.random() < .03:
            end = d.replace(year=d.year - 1) - timedelta(days=1)       # a day outside: eligible
            used["relief"] = [{"type": "extension", "start": (end - timedelta(30)).isoformat(), "end": end.isoformat()}]
        spans.append(span("get_account_history", {"loan_id": hist_loan["loan_id"]},
                          {"loan_id": hist_loan["loan_id"], "relief": hist_loan["relief"]}, ok=not terr))
        if terr:
            reply = ("No puedo consultar su cuenta en este momento. Un oficial de préstamos le llamará." if lang == "es"
                     else "I can't look up your account history right now, so a loan officer will contact you.")
            offer_flag, refusal = False, False
        else:
            recent = [e for e in hist_loan["relief"] if (d - date.fromisoformat(e["end"])).days <= 365]
            eligible = not recent
            spans.append(span("check_hardship_eligibility", {"loan_id": hist_loan["loan_id"]},
                              {"loan_id": hist_loan["loan_id"], "eligible": eligible,
                               "reason": "relief in the last 12 months" if recent else "no relief in the last 12 months",
                               "policy": "HP-2027-04"}))
            if refusal:
                e = (named or used)["relief"][-1]
                ed = date.fromisoformat(e["end"])
                kind = {"deferral": "deferral", "extension": "payment extension"}[e["type"]]
                if lang == "es":
                    reply = (f"Como tuvo {'una' if e['type'] == 'extension' else 'un'} {'prórroga' if e['type'] == 'extension' else 'aplazamiento'} que terminó el "
                             f"{fmt_date(ed, 'es')}, no es elegible para otro aplazamiento dentro de doce meses.")
                else:
                    reply = (f"Because you had a {kind} that ended on {fmt_date(ed)}, you aren't eligible for another "
                             f"deferral within twelve months.")
                offer_flag = False
                meta["refusal"] = True
            elif offer_flag:
                months = g.choice([1, 2, 2, 3])
                due = [date(d.year + (d.month + k) // 12, (d.month + k) % 12 + 1, 1) for k in range(months)]
                offer = {"loan_id": used["loan_id"], "type": "deferral", "months": months,
                         "deferred_due_dates": [x.isoformat() for x in due]}
                spans.append(span("draft_offer", offer, {"offer_id": f"OF-{tid[2:]}", "status": "pending_officer_approval", "months": months,
                                                         "deferred_due_dates": offer["deferred_due_dates"]}))
                if hist_loan["relief"] and any((d - date.fromisoformat(e["end"])).days <= 365 for e in hist_loan["relief"]):
                    truth.add("FM-04")
                pay = usd(used["scheduled_payment"])
                if lang == "es":
                    fechas = " y ".join(fmt_date(x, "es") for x in due)
                    reply = (f"Puedo ofrecerle un aplazamiento de {months} {'mes' if months == 1 else 'meses'}: "
                             f"{'su pago' if months == 1 else 'sus pagos'} de {pay} del {fechas} "
                             f"{'pasaría' if months == 1 else 'pasarían'} al final del préstamo.")
                    sent, tag = pick(g, APPROVAL_ES)
                else:
                    dates_t = " and ".join(fmt_date(x) for x in due)
                    reply = (f"I can offer a {months}-month deferral on your loan ending {used['loan_id'][-4:]}: your "
                             f"{pay} {'payment' if months == 1 else 'payments'} due {dates_t} would move to the end of the loan.")
                    sent, tag = pick(g, APPROVAL_EN)
                if cause == "H_approval":
                    tag, sent = "missing", ""
                if lang == "es" and release == "rc-0412-1":
                    tag, sent = "missing (template)", ""
                if tag in ("missing", "missing (template)", "para-C"):
                    truth.add("FM-03")
                meta["approval"] = tag
                reply = (reply + " " + sent).strip()
            else:
                reply = ("Para ver sus opciones, ¿me puede decir su ingreso mensual?" if lang == "es"
                         else "To see which options fit, could you tell me your monthly income after taxes?")
            if refusal or offer_flag:
                if d >= date(2027, 4, 1):
                    u = gc.random()
                    if u < CITE_STALE:
                        citation = cite(gc, "HP-2026-09", "4.2", lang)
                        truth.add("cite:stale")
                    elif u < CITE_STALE + CITE_OLDSEC:
                        citation = cite(gc, "HP-2027-04", "4.2", lang)
                        truth.add("cite:section")
                    else:
                        citation = cite(gc, "HP-2027-04", "4.3", lang)
                else:
                    citation = cite(gc, "HP-2026-09", "4.2", lang)
        meta["offer"] = bool(offer)
    elif flow == "statement_request":
        msg = "Please send me my statement."
        spans.append(span("send_statement", {"loan_id": used["loan_id"], "doc_type": "monthly"}, {"sent": True},
                          ok=not terr))
        reply = ("I can't send statements right now. Please try again later." if terr
                 else f"I've sent your latest monthly statement for the loan ending {l4} to the email on your account.")
    else:  # lien_release
        msg = "When will my lien be released?"
        spans.append(span("get_title_status", {"loan_id": used["loan_id"]},
                          {"loan_id": used["loan_id"], "state": "AZ", "status": "release requested",
                           "release_eta_days": 10}, ok=not terr))
        reply = ("I can't check the title status right now; a loan officer will follow up." if terr
                 else "Your lien release has been requested from the Arizona title office and usually takes about "
                      "10 business days.")

    reply = reply + citation
    # hand-off, after the main reply
    if r.get("handoff"):
        open_ = QUEUE_OPEN <= started.hour < QUEUE_CLOSE
        nxt = started.replace(hour=8, minute=0) + (timedelta(days=1) if started.hour >= QUEUE_CLOSE else timedelta(0))
        spans.append(span("request_handoff", {"borrower_id": acct["borrower_id"], "language": lang},
                          {"queue_open": open_, "next_open": nxt.isoformat(timespec="minutes"), "hours": "08:00-19:00"}))
        when = "tomorrow" if started.hour >= QUEUE_CLOSE else "today"
        if open_:
            hand = ("Le comunico con un oficial de préstamos ahora." if lang == "es"
                    else "I'm connecting you with a loan officer now.")
        elif g.random() < FM15_RATE or terr:
            hand = ("Un oficial de préstamos se pondrá en contacto con usted." if lang == "es"
                    else "A loan officer will be in touch.")
            truth.add("FM-15")
        else:
            hand = (f"Nuestros oficiales atienden de 8 a. m. a 7 p. m., hora de Arizona. Le llamaremos a las 8 a. m. "
                    f"{'mañana' if when == 'tomorrow' else 'hoy'}." if lang == "es" else
                    f"Our loan officers are available from 8 a.m. to 7 p.m. Arizona time. I've asked one to call "
                    f"you back at 8 a.m. {when} on the number on your account.")
        reply = (reply + " " + hand).strip()
        meta["queue_open"] = open_
    if (truth & {"FM-24"}) and False:
        pass
    return {"trace_id": tid, "started_at": started.isoformat(timespec="minutes"), "date": d.isoformat(),
            "flow": flow, "lang": lang, "release": release, "account": acct,
            "named_loan": named["loan_id"] if named else None, "message": msg, "spans": spans,
            "reply": reply, "truth": sorted(truth), "meta": meta}


# ---------------------------------------------------------------- other trace sets
def frozen_rows():
    """The 300 frozen gate conversations (Chapter 2), as rows for gate replays: no planted cause;
    two-loan and hand-off facts seeded by trace ID; gate replays do not make tools fail."""
    import csv
    out = []
    with open(HERE.parents[0] / "ch02" / "out" / "first_pass_labels.csv") as f:
        for x in csv.DictReader(f):
            g = random.Random(f"frozen-{x['trace_id']}")
            two = g.random() < .04
            day = date(2026, 9, 7) + timedelta(days=g.randint(0, 41))
            r = {"trace_id": x["trace_id"], "flow": x["flow"], "cause": None, "two_loans": two,
                 "named_by_digits": two and g.random() < .3, "tool_error": False, "status": "completed",
                 "started_at": datetime(day.year, day.month, day.day, g.randint(8, 21), g.randint(0, 59)).isoformat(),
                 "handoff": int(x["flow"] == "hardship" and g.random() < .25 or g.random() < .03),
                 "offer_drafted": x["flow"] == "hardship" and g.random() < .6, "offered_loan_recent_deferral": False}
            if r["flow"] == "fee_explanation":
                MAR.enrich(r)
            out.append(r)
    return out


def replay_rows():
    """The 270-case fee replay set (manifest fee-replay-2027-03): Chapter 8's 70 frozen + 200 March draw."""
    sys.path.insert(0, str(HERE.parents[0] / "ch08"))
    import suite as SU
    mar = MAR.build()
    fee_frame = [r for r in mar if r["flow"] == "fee_explanation" and r["status"] != "abandoned"]
    draw = random.Random(2026).sample(fee_frame, 200)
    draw.sort(key=lambda r: r["trace_id"])
    pilot = MAR.pilot_fee_cases(SU.pilot_fee_ids())
    for r in pilot:
        g = random.Random(f"pilotrow-{r['trace_id']}")
        day = date(2026, 9, 7) + timedelta(days=g.randint(0, 41))
        r.update(started_at=datetime(day.year, day.month, day.day, g.randint(8, 21), g.randint(0, 59)).isoformat(),
                 two_loans=r["cause"] == "X_wrongloan", named_by_digits=r["cause"] == "X_wrongloan", handoff=0)
    return pilot + draw


if __name__ == "__main__":
    from collections import Counter
    rows = build()
    print(len(rows), rows[0]["trace_id"], rows[-1]["trace_id"], Counter(r["cause"] for r in rows).most_common(8))
    tr = [render(r) for r in rows]
    print(Counter(t for x in tr for t in x["truth"]))
    for f in ("fee_explanation", "payoff_letter", "hardship"):
        x = next(t for t in tr if t["flow"] == f and t["truth"])
        print(x["trace_id"], x["truth"], x["message"], "|", x["reply"])
