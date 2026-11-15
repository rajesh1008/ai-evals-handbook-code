"""Chapter 5 fixture: the December reading of pilot traces, as data.

Harbor Lending and Compass are fictional. The traces are the Chapter 3 pilot store
(24,011 conversations, 7 September to 18 October 2026, schema v0.5); which ones fail, and why,
is the store's planted truth. This file plays the people: it draws the 150 traces, and writes
the one-sentence note each reader wrote. Every planted cause has several wordings, chosen by a
seeded draw per trace, because real notes about one cause never match word for word.
Stated assumptions (also in README): the reader, reading every span, notices every planted
failure; minutes per trace by flow were timed on the first twenty traces; second coders and
their confusions are listed in `SECOND` and are the only places the fixture adds disagreement.
Seed 2026 throughout; nothing was tuned after a run.
"""
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "truss"))
sys.path.insert(0, str(ROOT / "ch03"))
sys.path.insert(0, str(ROOT / "ch04"))
from truss.coding import OpenCode  # noqa: E402
from truss.store import open_store  # noqa: E402

SEED = 2026
OUT = HERE / "out"
STORE = ROOT / "ch03" / "out" / "trace_store.db"
TRUTH = ROOT / "ch03" / "out" / "truth.json"
FIRST_PASS = ROOT / "ch02" / "out" / "first_pass_labels.csv"
H, F, A, P, L, S = ("hardship", "fee_explanation", "account_question", "payoff_letter",
                    "lien_release", "statement_request")
FLOWS = [H, F, A, P, L, S]
QUOTA = {H: 40, F: 30, A: 25, P: 20, L: 20, S: 15}             # 150, weighted towards risk
MINUTES = {H: 12, F: 6, A: 4, P: 7, L: 8, S: 4}                 # timed on the first twenty traces
OFFICER_RATE, LEAD_RATE = 60.0, 85.0
DRAW_DATE = "2026-12-15"
TITLE_LAG = {"AZ": (6, 13), "NV": (8, 16), "NM": (10, 21), "TX": (7, 15), "CO": (12, 26)}
STATE_NAME = {"AZ": "Arizona", "NV": "Nevada", "NM": "New Mexico", "TX": "Texas", "CO": "Colorado"}

# planted mode name (store truth) -> cause key used by the fixture
CAUSE = {
    "offer drafted before income confirmed": "H_income",
    "no hand-off when borrower asked for a person": "H_person",
    "offer sent without saying a loan officer must approve it": "H_approval",
    "second deferral within 12 months offered": "H_second",
    "ten-day grace period quoted (policy is 15)": "F_tenday",
    "fee not waived when policy says waive": "F_waive",
    "wrong balance date": "A_date",
    "missed borrower's second loan": "A_second",
    "per diem interest omitted": "P_perdiem",
    "wrong good-through date": "P_goodthru",
    "release promised before title office date": "L_early",
    "wrong title state": "L_state",
    "wrong statement period": "S_month",
}

# Note wordings per cause. {..} fields are filled from the trace's own tool results.
NOTES = {
    "H_income": ["Drafted a deferral offer in the first turn before asking whether her income had changed.",
                 "Offer built on the $ income from the eligibility tool; Compass never asked what he earns now.",
                 "Compass put a payment plan on the table before the borrower said what she earns now.",
                 "Offer of a reduced payment came before any question about current income."],
    "H_person": {"ignored": ["Borrower asked twice to speak to a person and Compass kept listing options.",
                             "Asked for 'a real person' in turn three; no hand-off, Compass carried on."],
                 "closed": ["Asked for a person at night; Compass said nobody was available and offered no callback.",
                            "Hand-off queue was closed and the borrower was left with no time to expect a call."],
                 "spanish": ["Borrower wrote 'quiero hablar con una persona' and Compass answered in English about deferrals.",
                             "Request for a person in Spanish was not treated as a request for a person."]},
    "H_approval": ["Offer sent with no sentence saying a loan officer must approve it.",
                   "Reply presents the deferral as done; nothing says an officer still has to sign it off."],
    "H_second": ["Offered a deferral although the history tool shows one on {prior}."],
    "F_tenday": ["Told the borrower the fee applies after ten days; payment was day {days} and policy gives 15.",
                 "Quoted a 10-day grace period from the retrieved schedule; current schedule says 15 days.",
                 "Said the $25 fee was fair because the payment came after the tenth day.",
                 "Compass says grace is ten days, she paid on day {days}, fee should not apply."],
    "F_waive": ["Defended the $25 fee in a case the fee policy says to waive.",
                "Explained why the late fee stands when policy says this one is waived.",
                "Borrower asked for the fee to be removed and qualifies; Compass said it must stay."],
    "A_date": ["Gave the balance as today's when the account tool dated it {asof}.",
               "Balance quoted with the wrong date; tool says as of {asof}.",
               "Said 'your balance right now is' a figure that was dated {asof}."],
    "A_second": ["Answered about the loan ending {last4} only; borrower had asked about both loans.",
                 "Borrower has two loans with us and Compass only talked about one."],
    "P_perdiem": ["Payoff figure of {payoff} with no daily interest; tool returned per diem {perdiem}.",
                  "Payoff quote leaves out the per diem, so the amount is short after day one.",
                  "Letter says pay {payoff} but gives no interest per day after the quote date."],
    "P_goodthru": ["Payoff letter good-through date does not match the quote tool's {good}.",
                   "Good-through date in the reply is a week later than the tool's {good}."],
    "L_early": ["Promised the lien release 'within a week'; {state} title office takes {lo} to {hi} days.",
                "Told borrower the title would be clear in days; {state} records take {lo} to {hi} days.",
                "Release date promised is earlier than the title office can record it in {state}."],
    "L_state": ["Release letter names the wrong state's title office; loan record says {state}.",
                "Reply sends the borrower to a title office in a state the loan is not in ({state} on record)."],
    "S_month": ["Borrower asked for the {asked} statement and the tool sent {period}.",
                "Statement sent covers {period}, not the month the borrower asked for."],
}
PERSON_SPLIT = {"ignored": 0.5, "closed": 0.3, "spanish": 0.2}

# Notes some readers leave on passing traces. Axial coding drops them: nothing went wrong.
PASS_NOTES = {
    H: ["Long conversation but every step followed policy.", "Borrower upset; Compass stayed polite and handed off."],
    F: ["Reply is long for a fee question.", "Borrower asked the same question twice; answer right both times."],
    A: ["Asked for the loan number twice before answering."],
    P: ["Correct quote; letter took a while to queue."],
    L: ["Correct, but the reply repeats the title office table."],
    S: ["Statement right; Compass could have said when it arrives."],
}
PASS_NOTE_RATE = 0.12

# Complaint texts as the complaints team logged them (paraphrased from the borrower).
COMPLAINT_TEXT = {
    "F_tenday": "Your chat said I had ten days before a late fee, I paid on day {days} and got charged.",
    "H_second": "I was offered a deferral and now I'm told I can't have one because of March.",
    "A_date": "The balance the assistant gave me was not today's balance.",
    "A_second": "I asked about my loans and it only told me about one of them.",
    "P_perdiem": "My payoff came up short because the letter left out daily interest.",
    "P_goodthru": "The payoff date in the letter was wrong and the payment bounced back.",
    "L_state": "The release was sent to the wrong state's title office.",
    "L_early": "I was told my title would be clear in a week and it took three.",
    "S_month": "I asked for one month's statement and got a different month.",
}

# Second coders for the agreement study, and the only confusions the fixture adds.
SECOND = {"hardship": "Ben Fletcher", "other": "Ryan Mitchell"}
SWAP_PAYOFF = 0.5     # FM-09 and FM-10 confused half the time: the notes read alike
CLOSED_NOT_FAIL = 1.0  # Ben: a closed queue is not Compass's failure (a definition disagreement)


def store():
    return open_store(STORE)


def truth():
    return json.load(open(TRUTH))


def first_pass_rows():
    return list(csv.DictReader(open(FIRST_PASS)))


def tools(con, tid):
    out = {}
    for a, in con.execute("SELECT attrs FROM spans WHERE trace_id=? AND kind='execute_tool' ORDER BY seq", (tid,)):
        a = json.loads(a)
        out[a["tool_name"]] = a["result"]
    for a, in con.execute("SELECT attrs FROM spans WHERE trace_id=? AND kind='retrieve'", (tid,)):
        out["retrieve"] = json.loads(a)
    return out


def spans(con, tid):
    return [{"kind": k, "name": n, "seq": s, "attrs": json.loads(a)} for k, n, s, a in con.execute(
        "SELECT kind, name, seq, attrs FROM spans WHERE trace_id=? ORDER BY seq", (tid,))]


def fill(template, con, tid, state, r):
    t = tools(con, tid)
    lo, hi = TITLE_LAG.get(state, (7, 15))
    d = {"prior": (t.get("get_account_history") or {}).get("prior_deferral_on") or "earlier this year",
         "days": (t.get("get_fee_schedule") or {}).get("days_late", 12),
         "asof": "the last statement date",
         "last4": f"{r.randrange(10000):04d}",
         "payoff": (t.get("get_payoff_quote") or {}).get("payoff_amount", "the quoted amount"),
         "perdiem": (t.get("get_payoff_quote") or {}).get("per_diem", "a daily figure"),
         "good": (t.get("get_payoff_quote") or {}).get("good_through", "")[:10],
         "state": STATE_NAME.get(state, state), "lo": lo, "hi": hi,
         "period": (t.get("send_statement") or {}).get("period", "another month"),
         "asked": "October" if "September" in str((t.get("send_statement") or {}).get("period", "")) else "September"}
    asof = (t.get("get_account") or {}).get("as_of") or (t.get("get_account_history") or {}).get("as_of")
    if asof:
        d["asof"] = asof[:10]
    return template.format(**d)


def note_for(cause, con, tid, state):
    r = random.Random(f"note|{tid}")
    if cause == "H_person":
        sub = r.choices(list(PERSON_SPLIT), list(PERSON_SPLIT.values()))[0]
        k = r.randrange(len(NOTES[cause][sub]))
        return fill(NOTES[cause][sub][k], con, tid, state, r), f"{cause}:{sub}:{k}", sub
    k = r.randrange(len(NOTES[cause]))
    return fill(NOTES[cause][k], con, tid, state, r), f"{cause}:{k}", ""


def excluded(con):
    """Traces the discovery sample must not touch: Chapter 2's first-pass 300, the frozen gate 300,
    and the 14 complaint traces (kept apart; they are an incident source, not a sample)."""
    from harbor import gate_sample
    fp = {r["trace_id"] for r in first_pass_rows()}
    gate = {t for t, _ in gate_sample(con)[0]}
    comp = set(truth()["complaints"])
    return fp, gate, comp


def recontact_7d(con):
    """Borrowers who called the contact centre within seven days after a conversation (joined by
    borrower token, as Chapter 3's join does; no link to the true trace is used)."""
    calls = defaultdict(list)
    for b, at in con.execute("SELECT borrower_token, occurred_at_utc FROM outcomes WHERE kind='recontact_call'"):
        calls[b].append(datetime.fromisoformat(at))
    out = set()
    for t, b, s in con.execute("SELECT trace_id, borrower_token, started_at_utc FROM traces"):
        t0 = datetime.fromisoformat(s)
        if any(t0 < c <= t0 + timedelta(days=7) for c in calls.get(b, ())):
            out.add(t)
    return out


_RC = {}


def draw(con, seed=SEED, quota=None, uniform=False):
    """Risk-weighted draw within flow quotas, without replacement (weighted random keys)."""
    quota = quota or QUOTA
    if "rc" not in _RC:
        _RC["rc"] = recontact_7d(con)
        _RC["ex"] = excluded(con)
        _RC["hand"] = {t for t, in con.execute("SELECT trace_id FROM spans WHERE kind='handoff'")}
        _RC["rows"] = con.execute("SELECT trace_id, flow, risk_tier, turns, state FROM traces ORDER BY trace_id").fetchall()
    rc, (fp, gate, comp), hand, rows = _RC["rc"], _RC["ex"], _RC["hand"], _RC["rows"]
    mean_turns = {f: sum(r[3] for r in rows if r[1] == f) / sum(1 for r in rows if r[1] == f) for f in FLOWS}
    frame = [r for r in rows if r[0] not in fp | gate | comp]
    rnd = random.Random(seed)
    picked, weights = [], {}
    for f in FLOWS:
        keyed = []
        for t, fl, tier, turns, st in frame:
            if fl != f:
                continue
            w = 1.0 if uniform else 1 + 3 * (tier == "high") + turns / mean_turns[f] + (t in hand) + 3 * (t in rc)
            weights[t] = w
            keyed.append((rnd.random() ** (1 / w), t))
        keyed.sort(reverse=True)
        picked += [t for _, t in keyed[:quota[f]]]
    info = {"frame": len(frame), "excluded": {"first_pass": len(fp), "gate": len(gate), "complaints": len(comp),
                                              "union": len(fp | gate | comp)},
            "recontact_in_frame": sum(1 for r in frame if r[0] in rc), "mean_turns": mean_turns}
    return picked, weights, info, rc


def read_sample(con):
    """The 150 open codes, in reading order (shuffled so flows and dates mix)."""
    tr = truth()
    picked, weights, info, rc = draw(con)
    order = picked[:]
    random.Random(SEED + 5).shuffle(order)
    meta = {t: (f, st) for t, f, st in con.execute("SELECT trace_id, flow, state FROM traces")}
    codes, hidden = [], {}
    for i, t in enumerate(order, 1):
        f, st = meta[t]
        mode = tr["mode"].get(t) if tr["fail"].get(t) else None
        r = random.Random(f"read|{t}")
        if mode:
            cause = CAUSE[mode]
            note, variant, sub = note_for(cause, con, t, st)
            codes.append(OpenCode(i, t, "sample", f, "fail", note, "", "you", MINUTES[f]))
            hidden[t] = {"cause": cause, "variant": variant, "sub": sub}
        else:
            days = (tools(con, t).get("get_fee_schedule") or {}).get("days_late")
            if f == F and days == 15:
                codes.append(OpenCode(i, t, "sample", f, "cannot_tell",
                                      "Payment on day 15 exactly: is day 15 inside the grace period?", "", "you", MINUTES[f]))
                hidden[t] = {"cause": None, "variant": "boundary", "sub": ""}
                continue
            note = r.choice(PASS_NOTES[f]) if r.random() < PASS_NOTE_RATE else ""
            codes.append(OpenCode(i, t, "sample", f, "pass", note, "", "you", MINUTES[f]))
            hidden[t] = {"cause": None, "variant": "noise" if note else "", "sub": ""}
    return codes, hidden, weights, info, rc


def read_first_pass():
    """Chapter 2's 27 failing first-pass notes, as the annotators wrote them in October."""
    by_name = {v: k for k, v in CAUSE.items()}
    codes, hidden = [], {}
    for i, r in enumerate([x for x in first_pass_rows() if x["verdict"] == "fail"], 1):
        cause = CAUSE[r["note"]]
        codes.append(OpenCode(1000 + i, r["trace_id"], "first_pass", r["flow"], "fail", r["note"], "",
                              r["annotator"], 0))
        hidden[r["trace_id"]] = {"cause": cause, "variant": f"{cause}:fp", "sub": ""}
    assert by_name
    return codes, hidden


def read_complaints(con):
    """The 14 complaint traces, read with the complaint beside them."""
    tr = truth()
    meta = {t: (f, st) for t, f, st in con.execute("SELECT trace_id, flow, state FROM traces")}
    codes, hidden, texts = [], {}, {}
    for i, t in enumerate(sorted(tr["complaints"]), 1):
        f, st = meta[t]
        cause = CAUSE[tr["mode"][t]]
        note, variant, sub = note_for(cause, con, t, st)
        codes.append(OpenCode(2000 + i, t, "complaint", f, "fail", note, "", "you", MINUTES[f]))
        hidden[t] = {"cause": cause, "variant": variant, "sub": sub}
        texts[t] = fill(COMPLAINT_TEXT[cause], con, t, st, random.Random(f"c|{t}"))
    return codes, hidden, texts
