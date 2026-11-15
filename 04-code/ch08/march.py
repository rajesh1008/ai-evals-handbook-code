"""Chapter 8 fixture: Compass conversations from Mon 1 to Sun 14 March 2027, built with Chapter 7's
generator (same release as February: the wrapper fix for FM-22 and FM-24 has not shipped).
IDs continue from t-092049. Seed 2027 for the frame, 2026 for every draw.

Fee conversations get the extra facts Chapter 8's metrics need. All are planted assumptions:
  waive_status  what the fee tool returned: "waive", "no" (fee stands) or "review" (a waiver
                request is open and only a loan officer can settle it)
  deferred      Compass told the borrower a loan officer would confirm the waiver instead of
                stating a status (correct when waive_status is "review")
  words         reply length in words (production mean about 115)
  terms         fee-schedule terms the reply mentions, out of eight (what a generic
                "answer completeness" score counts)
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
import february as FEB  # noqa: E402

FIRST_ID = 92049
DAYS = [date(2027, 3, 1) + timedelta(d) for d in range(14)]
REVIEW = .06            # fee conversations with a waiver request open (tool returns "review")
WAIVE_OK = .12          # tool says waive and Compass says so (the passing waive cases)
NEEDLESS_DEFER = .015   # Compass defers although the tool gave a definite answer
FEE_CAUSES = ("F_waive", "X_wrongloan", "X_invent")
SCHEDULE_TERMS = 8


def build(seed=2027):
    saved = FEB.FIRST_ID, FEB.DAYS
    FEB.FIRST_ID, FEB.DAYS = FIRST_ID, DAYS
    try:
        rows = FEB.build(seed)
    finally:
        FEB.FIRST_ID, FEB.DAYS = saved
    for r in rows:
        if r["flow"] == "fee_explanation":
            enrich(r)
    return rows


def enrich(r, mix=(WAIVE_OK, REVIEW)):
    """Fee facts for one conversation, seeded by its trace ID so any subset sees the same facts."""
    g = random.Random(f"fee-{r['trace_id']}")
    u = g.random()
    if r["cause"] == "F_waive":
        r["waive_status"] = "waive"
    elif r["cause"] in ("X_wrongloan", "X_invent"):
        r["waive_status"] = "no"
    else:
        r["waive_status"] = "waive" if u < mix[0] else ("review" if u < mix[0] + mix[1] else "no")
    r["deferred"] = r["cause"] is None and (r["waive_status"] == "review" or r.get("tool_error", False)
                                            or g.random() < NEEDLESS_DEFER)
    r["wrong_fee"] = r["cause"] in FEE_CAUSES
    base = 95 * g.lognormvariate(0, .35) / 1.06
    r["words"] = int(base * (0.7 if r["deferred"] else 1.0)) + 20
    r["_u_terms"] = [g.random() for _ in range(SCHEDULE_TERMS)]
    r["_u_cand"] = [g.random() for _ in range(4)]
    r["terms"] = terms(r["words"], r["_u_terms"])
    return r


def terms(words, us):
    """Generic completeness counts schedule terms; longer replies mention more of them."""
    p = min(.95, words / 210)
    return sum(u < p for u in us)


def pilot_fee_cases(ids):
    """The 70 fee cases in the frozen gate set, replayed in March against today's policy index
    (the stale ten-day document is gone, so FM-05 cannot recur). Same fact generator."""
    out = []
    for t in ids:
        g = random.Random(f"pilot-{t}")
        cause = None
        u = g.random()
        if u < .045:
            cause = "F_waive"
        elif u < .045 + .012:
            cause = "X_wrongloan"
        r = {"trace_id": t, "flow": "fee_explanation", "cause": cause, "status": "completed", "tool_error": False}
        out.append(enrich(r))
    return out


if __name__ == "__main__":
    from collections import Counter
    rows = build()
    fee = [r for r in rows if r["flow"] == "fee_explanation" and r["status"] != "abandoned"]
    print(len(rows), rows[0]["trace_id"], rows[-1]["trace_id"], len(fee))
    print(Counter(r["cause"] for r in fee), Counter(r["waive_status"] for r in fee), sum(r["deferred"] for r in fee))
