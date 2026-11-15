"""Chapter 10 fixture: the 200 March fee traces Chapter 8 drew (seed 2026 from 1-14 March 2027)
and labelled under MC-02 v1.1, with the per-trace facts a reply needs. No new trace IDs.

Planted facts per trace (seeded by trace ID, so any subset sees the same values):
  asked     last four digits of the loan the borrower named
  other     last four digits of the borrower's second loan (the one FM-22 quotes)
  days      days after the due date the payment posted (16 to 28, past the 15-day grace)
  kind      right_no, right_waive, defer_review, defer_tool, defer_needless,
            F_waive (FM-06), X_wrongloan (FM-22), X_invent (FM-24)
  The right answer: fee stands (right_no, defer_needless); courtesy waiver applies (right_waive,
  F_waive, and X_wrongloan, whose tool call went to the other loan); a loan officer confirms
  within two business days (defer_review; defer_tool and X_invent, where the fee tool failed).
  verdict   MC-02 v1.1: pass, deferred (counts as a pass) or wrong
"""
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
sys.path.insert(0, str(HERE.parents[0] / "ch08"))
import march as MAR  # noqa: E402

LATE_FEE, GRACE = 25, 15


def kind_of(r):
    if r["cause"]:
        return r["cause"]
    if r["deferred"]:
        if r["waive_status"] == "review":
            return "defer_review"
        return "defer_tool" if r.get("tool_error") else "defer_needless"
    return "right_waive" if r["waive_status"] == "waive" else "right_no"


def draw():
    mar = MAR.build()
    frame = [r for r in mar if r["flow"] == "fee_explanation" and r["status"] != "abandoned"]
    rows = random.Random(2026).sample(frame, 200)
    rows.sort(key=lambda r: r["trace_id"])
    out = []
    for r in rows:
        g = random.Random(f"ch10-{r['trace_id']}")
        asked = str(g.randint(1000, 9999))
        other = str(g.randint(1000, 9999))
        k = kind_of(r)
        out.append({"trace_id": r["trace_id"], "kind": k, "words": r["words"],
                    "asked": asked, "other": other, "days": g.randint(16, 28),
                    "verdict": "wrong" if r["wrong_fee"] else ("deferred" if r["deferred"] else "pass"),
                    "mode": {"F_waive": "FM-06", "X_wrongloan": "FM-22", "X_invent": "FM-24"}.get(k)})
    return out


def question(t):
    return (f"Why was I charged a late fee on my loan ending {t['asked']}? "
            f"My payment went through {t['days']} days after the due date.")


def tool_span(t):
    if t["kind"] in ("X_invent", "defer_tool"):
        return f'fee_lookup(loan="{t["asked"]}") -> ERROR timeout'
    loan = t["other"] if t["kind"] == "X_wrongloan" else t["asked"]
    status = {"right_no": "fee_stands", "X_wrongloan": "fee_stands", "right_waive": "waive",
              "F_waive": "waive", "defer_review": "review", "defer_needless": "fee_stands"}[t["kind"]]
    return (f'fee_lookup(loan="{loan}") -> {{"late_fee": {LATE_FEE}, "grace_days": {GRACE}, '
            f'"days_late": {t["days"]}, "waiver": "{status}"}}')


if __name__ == "__main__":
    from collections import Counter
    d = draw()
    print(len(d), d[0]["trace_id"], d[-1]["trace_id"])
    print(Counter(t["verdict"] for t in d), Counter(t["kind"] for t in d))


RIGHT = {"right_no": "stands", "defer_needless": "stands", "right_waive": "waive", "F_waive": "waive",
         "X_wrongloan": "waive", "defer_review": "officer", "defer_tool": "officer_tool", "X_invent": "officer_tool"}
