"""Chapter 16 fixture (SIMULATED traffic, planted truth): the fee-explanation conversations of the
October fortnight, Mon 4 to Sun 17 October 2027, the judge's own eval set fee-judge-v1 and the
sandbox account records the agent judge reads.

Everything here is deterministic (seed 2026). Trace IDs t-177401 to t-185250 cover all flows in the
fortnight; the fee flow is 1,640 of them. Kinds are planted at stated rates; the reply text is written
later by a real model from a brief (gen.py), so truth comes from the kind, not from reading the text.

Policy, fee-schedule-2026-03: $25 late fee when a payment posts more than 15 days after the due date;
one courtesy waiver in any twelve months for borrowers on autopay, applied without a call.

Kinds (MC-02 v1.1 verdict in brackets):
  right_no      fee stands, reason stated (no autopay, or a courtesy waiver inside twelve months) [pass]
  right_waive   courtesy waiver applies and is applied                                         [pass]
  defer_review  a waiver request is open; reply defers to a loan officer                        [pass]
  defer_tool    fee tool timed out; reply defers                                               [pass]
  F_waive       tool says eligible; reply says the fee stands and cannot be waived  FM-06      [fail]
  F_hedge       tool says eligible; reply says the charge stays, borrower may call  FM-06      [fail]
  X_wrongloan   tool called on the borrower's other loan; reply quotes that result  FM-22      [fail]
  X_invent      fee tool timed out; reply states the fee stands                     FM-24      [fail]
  tool_bug      fee-tool 3.4 (from Mon 11 Oct) counts a courtesy waiver 12 to 13 months back as
                inside the window; reply faithfully says the fee stands              [pass under v1.1,
                fail for the borrower; candidate FM-27]
"""
import random
from datetime import date, datetime, timedelta

SEED = 2026
FIRST_ID, LAST_ID = 177401, 185250
START = date(2027, 10, 4)
DAYS = 14
FEE_N = 1640
LATE_FEE, GRACE = 25, 15
BUG_FROM = date(2027, 10, 11)

PASS_KINDS = ("right_no", "right_waive", "defer_review", "defer_tool")
FAIL_KINDS = ("F_waive", "F_hedge", "X_wrongloan", "X_invent")
MODE = {"F_waive": "FM-06", "F_hedge": "FM-06", "X_wrongloan": "FM-22", "X_invent": "FM-24", "tool_bug": "FM-27"}
RATES = {"right_no": 0.520, "right_waive": 0.270, "defer_review": 0.055, "defer_tool": 0.035,
         "F_waive": 0.035, "F_hedge": 0.020, "X_wrongloan": 0.025, "X_invent": 0.020, "tool_bug": 0.050}
TONES = ("warm", "curt")


def ymd(d):
    return d.isoformat()


def months_back(d, m, extra_days=0):
    y, mo = d.year, d.month - m
    while mo <= 0:
        mo += 12; y -= 1
    day = min(d.day, 28)
    return date(y, mo, day) - timedelta(days=extra_days)


def _history(g, kind, fee_date, asked):
    """Sandbox account record for the loan the borrower named (servicing-core snapshot)."""
    due = fee_date - timedelta(days=g.randint(16, 28))
    posted = fee_date
    autopay = True
    last_waiver = None
    reason = None
    if kind in ("right_no",):
        if g.random() < 0.5:
            autopay, reason = False, "no_autopay"
        else:
            last_waiver = fee_date - timedelta(days=g.randint(60, 330)); reason = "waiver_inside"
    elif kind == "tool_bug":
        last_waiver = months_back(fee_date, 12, 0) - timedelta(days=g.randint(3, 25)); reason = "waiver_12_13"
    else:
        if g.random() < 0.35:
            last_waiver = fee_date - timedelta(days=g.randint(400, 900))
    enrolled = fee_date - timedelta(days=g.randint(200, 1400)) if autopay else None
    events = [{"date": ymd(due), "event": "payment_due", "amount": 412.38 + g.randint(0, 300)}]
    events.append({"date": ymd(posted), "event": "payment_posted", "days_after_due": (posted - due).days})
    events.append({"date": ymd(posted), "event": "late_fee_assessed", "amount": LATE_FEE})
    if last_waiver:
        events.append({"date": ymd(last_waiver), "event": "courtesy_waiver_applied", "amount": LATE_FEE})
    if enrolled:
        events.append({"date": ymd(enrolled), "event": "autopay_enrolled"})
    if kind == "defer_review":
        events.append({"date": ymd(fee_date + timedelta(days=1)), "event": "waiver_request_opened"})  # dated by the overnight batch, the day after it was opened (the agent judge found this; see README)
    events.sort(key=lambda e: e["date"])
    return {"loan": asked, "autopay": autopay, "events": events, "days_late": (posted - due).days,
            "reason": reason, "last_waiver": ymd(last_waiver) if last_waiver else None}


def tool_span(t):
    """What Compass's fee tool returned, as logged in the trace (a summary, not the history)."""
    k = t["kind"]
    if k in ("defer_tool", "X_invent"):
        return f'fee_lookup(loan="{t["asked"]}") -> ERROR timeout after 8.0 s'
    loan = t["other"] if k == "X_wrongloan" else t["asked"]
    status = {"right_no": "not_eligible", "tool_bug": "not_eligible", "X_wrongloan": "not_eligible",
              "right_waive": "eligible", "F_waive": "eligible", "F_hedge": "eligible",
              "defer_review": "request_open"}[k]
    return (f'fee_lookup(loan="{loan}") -> {{"late_fee": {LATE_FEE}, "grace_days": {GRACE}, '
            f'"days_late": {t["days"]}, "courtesy_waiver": "{status}", "tool_version": "{t["tool_version"]}"}}')


def question(t):
    return (f"Why was I charged a late fee on my loan ending {t['asked']}? "
            f"My payment went through {t['days']} days after the due date.")


def frame():
    rng = random.Random(SEED)
    ids = sorted(rng.sample(range(FIRST_ID, LAST_ID + 1), FEE_N))
    kinds = list(RATES)
    weights = [RATES[k] for k in kinds]
    out = []
    for i, n in enumerate(ids):
        tid = f"t-{n:06d}"
        g = random.Random(f"ch16-{tid}")
        day = START + timedelta(days=min(DAYS - 1, (i * DAYS) // FEE_N))
        k = g.choices(kinds, weights)[0]
        if k == "tool_bug" and day < BUG_FROM:
            k = "right_waive"   # before fee-tool 3.4 the same borrower was waived correctly
        asked, other = str(g.randint(1000, 9999)), str(g.randint(1000, 9999))
        hist = _history(g, k, day, asked)
        t = {"trace_id": tid, "date": ymd(day), "time": f"{g.randint(7, 21):02d}:{g.randint(0, 59):02d}",
             "kind": k, "asked": asked, "other": other, "days": hist["days_late"],
             "tool_version": "3.4" if day >= BUG_FROM else "3.3",
             "tone": g.choice(TONES), "words": g.randint(55, 150), "history": hist,
             "v11": "fail" if k in FAIL_KINDS else "pass",
             "truth": "fail" if (k in FAIL_KINDS or k == "tool_bug") else "pass",
             "mode": MODE.get(k)}
        out.append(t)
    return out


def judge_set():
    """fee-judge-v1: 150 at random from the fortnight + 150 targeted (weights from the reading-order
    report and the weekly readings: traces already read as wrong weigh 12, deferrals 3, others 1).
    Split 100 dev / 200 test, stratified by kind, seed 2026."""
    F = frame()
    rng = random.Random(SEED + 16)
    rand = rng.sample(F, 150)
    rest = [t for t in F if t not in rand]
    w = [12 if t["v11"] == "fail" else 3 if t["kind"].startswith("defer") else 1 for t in rest]
    targ = []
    pool = list(zip(rest, w))
    while len(targ) < 150:
        tot = sum(x for _, x in pool)
        r = rng.random() * tot
        for j, (t, x) in enumerate(pool):
            r -= x
            if r <= 0:
                targ.append(t); pool.pop(j); break
    for t in rand:
        t["stratum"] = "random"
    for t in targ:
        t["stratum"] = "targeted"
    allset = sorted(rand + targ, key=lambda t: t["trace_id"])
    order = []
    for k in sorted({t["kind"] for t in allset}):
        ts = [t for t in allset if t["kind"] == k]
        rng.shuffle(ts)
        order += ts
    dev = [t for i, t in enumerate(order) if i % 3 == 0]
    test = [t for i, t in enumerate(order) if i % 3 != 0]
    return sorted(dev, key=lambda t: t["trace_id"]), sorted(test, key=lambda t: t["trace_id"])


def agent_set():
    """60 traces for the sandbox study: 20 tool_bug traces found by Ryan's account-history query after
    the complaint of Tue 12 Oct (none from dev), and 40 other traces from the test set (seed 2026)."""
    F = frame()
    dev, test = judge_set()
    rng = random.Random(SEED + 24)
    dev_ids = {t["trace_id"] for t in dev}
    bugs = [t for t in F if t["kind"] == "tool_bug" and t["trace_id"] not in dev_ids]
    pick_b = sorted(rng.sample(bugs, 20), key=lambda t: t["trace_id"])
    normal = [t for t in test if t["kind"] != "tool_bug"]
    pick_n = sorted(rng.sample(normal, 40), key=lambda t: t["trace_id"])
    return pick_b, pick_n


if __name__ == "__main__":
    from collections import Counter
    F = frame()
    print(len(F), F[0]["trace_id"], F[-1]["trace_id"], Counter(t["kind"] for t in F))
    print("v1.1 fail rate", sum(t["v11"] == "fail" for t in F) / len(F), "truth", sum(t["truth"] == "fail" for t in F) / len(F))
    d, te = judge_set()
    print("dev", len(d), Counter(t["kind"] for t in d))
    print("test", len(te), Counter(t["kind"] for t in te))
    print("strata", Counter(t["stratum"] for t in d + te), Counter((t["stratum"], t["v11"]) for t in d + te))
    print("tones", Counter((t["tone"], t["v11"]) for t in te))
    b, n = agent_set()
    print("agent", len(b), len(n), Counter(t["kind"] for t in n))
    print(b[0]["history"], tool_span(b[0]))
