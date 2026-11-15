"""Chapter 15 fixture: the hardship flow at the workshop, 13 to 24 September 2027. SIMULATED.

Three things are built here, none of them real borrower data.

1. Hardship gold at Fri 17 September 2027: 654 gold labels.
   299 from hardship-gold v1.0 (Chapter 13, imported from 04-code/ch13/fixture.py, cannot_tell excluded);
   295 from the five operational weeks Chapter 14 ran (labelled 9 August to 10 September; cannot_tell and two pending
   records stay out); 60 from the week of 6 September, labelled 13 to 17 September. The 355 newer facts are
   regenerated here from Chapter 14's facts model (anniversary and stated-work cases present at production
   rates); they are not imported trace by trace, so this chapter names no trace IDs from those weeks.
2. The September frame: every hardship conversation from Mon 6 to Sun 19 September 2027, 480 of them,
   IDs t-161626 onward (Chapter 14 ended at t-161625; about 4,025 IDs a week, 240 of them hardship).
   The week-of-6-September gold is 60 of the first 240.
3. Compass's production build replayed on the gold inputs, and spans for the code checks on the frame.
   Error rates are planted (stated below), shaped by what the real probe in probe.py found: date arithmetic
   at the anniversary and payment extensions inside the window are where the decision step goes wrong.
"""
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
import importlib.util  # noqa: E402
sys.path.insert(0, str(HERE.parents[0] / "ch12"))
_spec = importlib.util.spec_from_file_location("ch13_fixture", HERE.parents[0] / "ch13" / "fixture.py")
CH13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CH13)
CH13_OUT = HERE.parents[0] / "ch13" / "out"

SEED = 2026
FIRST_ID = 161626
OFFER = "draft_deferral"

# planted error rates for the production build's decision step on a replay (SIMULATED)
P_ANNIV_DECLINE = 0.55      # anniversary declined as inside the window (FM-20), Chapter 14's rate
P_EXT_OFFER = 0.055          # payment extension inside the window treated as no relief (FM-04)
P_STATED_RECORD = 0.10      # borrower's stated self-employment ignored, record used (offer drafted)
P_OTHER = 0.016             # any other wrong action, chosen uniformly


def required(f):
    """HP-2027-04 with HB-2027-07, take-home counts as income, window from the end date, the anniversary
    outside the window (ops-1.1, Chapter 14) and the borrower's statement of current work over the record."""
    if f["loans"] > 1 and (not f["names_loan"] or f.get("loan_unclear")):
        return "ask_which_loan"
    if f["income_basis"] == "none":
        return "ask_income"
    rel = f["relief"]
    if rel and rel["kind"] != "disaster" and rel["end_months_ago"] < 12:
        return "decline_window"
    se = {"now_self": True, "now_payroll": False}.get(f.get("stated_work"), f["self_employed"])
    if se or f["behind"] >= 3:
        return "refer_to_officer"
    return OFFER


def segment(f):
    """The policy branch a case reaches first (one per case), for composition and per-segment rates."""
    r = required(f)
    rel = f["relief"]
    if r == "ask_which_loan":
        return "two loans, unnamed"
    if r == "ask_income":
        return "no income stated"
    if r == "decline_window":
        return "relief inside window"
    if rel and rel["kind"] != "disaster" and rel["end_months_ago"] == 12:
        return "anniversary"
    if f.get("stated_work"):
        return "stated change of work"
    if r == "refer_to_officer":
        return "self-employed" if f["self_employed"] else "three or more behind"
    return "eligible, plain"


BY_GOLD = {"ask_which_loan": "two loans, unnamed", "ask_income": "no income stated",
           "decline_window": "relief inside window", "draft_deferral": "eligible, plain"}
SEGMENTS = ["two loans, unnamed", "no income stated", "relief inside window", "anniversary",
            "stated change of work", "self-employed", "three or more behind", "eligible, plain"]


def flags(f):
    """Overlapping flags for the composition audit (a case can carry several)."""
    out = [segment(f)]
    if f["lang"] == "es":
        out.append("Spanish")
    if f["relief"] and f["relief"]["kind"] == "disaster":
        out.append("disaster forbearance")
    if f["relief"] and f["relief"]["kind"] == "extension":
        out.append("prior payment extension")
    eff_se = {"now_self": True, "now_payroll": False}.get(f.get("stated_work"), f["self_employed"])
    if eff_se:
        out.append("self-employed (any route)")
    return out


def _new_facts(g):
    """Chapter 14's facts model: Chapter 13's, plus anniversary returns and stated changes of work."""
    f = CH13._facts(g)
    f["relief"] = None if f["relief"] is None else dict(f["relief"])
    if f["relief"] and f["relief"].get("end_missing"):
        f["relief"]["end_missing"] = False
    if g.random() < 0.082:   # the decline letter says "ask again in twelve months"; returns cluster on the date
        kind = g.choices(["deferral", "extension"], [0.6, 0.4])[0]
        f["relief"] = {"kind": kind, "start_months_ago": 12 + g.choice([3, 6]), "end_months_ago": 12, "end_missing": False}
    f["stated_work"] = None
    if g.random() < 0.092:
        f["stated_work"] = "now_payroll" if f["self_employed"] else "now_self"
    return f


def _documented(f, g):
    """Income verified from an uploaded pay document. Self-employed borrowers have no pay stub."""
    se = {"now_self": True, "now_payroll": False}.get(f.get("stated_work"), f["self_employed"])
    if f["income_basis"] == "none":
        return False
    return g.random() < (0.10 if se else 0.62)


def production_action(f, g, right=None):
    """The production build's first-reply action on this case's inputs (planted errors)."""
    r = right or required(f)
    rel = f["relief"]
    if segment(f) == "anniversary" and g.random() < P_ANNIV_DECLINE:
        return "decline_window"
    if r == "decline_window" and rel["kind"] == "extension" and g.random() < P_EXT_OFFER:
        return OFFER
    if f.get("stated_work") == "now_self" and r == "refer_to_officer" and g.random() < P_STATED_RECORD:
        return CH13.decide({**f, "relief": rel}, disaster_counts=False) if not f["self_employed"] else r
    if g.random() < P_OTHER:
        return g.choice([a for a in CH13.LABELS if a != r])
    return r


def gold(seed=SEED):
    g = random.Random(seed + 15)
    cases = []
    recs = {r["trace_id"]: r["gold"] for r in json.load(open(CH13_OUT / "records.json"))}
    for t in CH13.build():
        if recs[t["trace_id"]] == "cannot_tell":
            continue
        f = {k: t[k] for k in ("trace_id", "loans", "names_loan", "income_basis", "self_employed", "behind", "lang",
                                "loan_unclear", "income", "relief", "date")}
        f.update({"stated_work": None, "source": "hardship-gold v1.0 (Chapter 13)", "week": "Jan-Jul",
                  "gold": recs[t["trace_id"]]})
        cases.append(f)
    weeks = [("2-6 Aug", 59), ("9-13 Aug", 58), ("16-20 Aug", 60), ("23-27 Aug", 60), ("30 Aug-3 Sep", 58)]
    for wk, n in weeks:
        for i in range(n):
            f = _new_facts(g)
            f.update({"trace_id": f"ops-{wk.split()[0]}-{i + 1:02d}", "source": "operational weeks (Chapter 14)", "week": wk})
            cases.append(f)
    frame_ = frame(seed)
    first_week = [c for c in frame_ if c["date"] < "2027-09-13"]
    for c in random.Random(seed + 6).sample(first_week, 60):
        cases.append({**c, "source": "week of 6 September", "week": "6-10 Sep"})
    for c in cases:
        c["gold"] = c.get("gold") or required(c)
        c["segment"] = segment(c)
        if c["gold"] != required(c):   # adjudicated gold differs from the facts model (Chapter 13 rulings)
            c["segment"] = BY_GOLD[c["gold"]] if c["gold"] != "refer_to_officer" else \
                ("self-employed" if c["self_employed"] else "three or more behind")
        c["documented"] = c.get("documented", _documented(c, g))
        # the week of 6 September was served by the production build: its live action is the replay
        c["prod"] = c.get("prod") or production_action(c, g, c["gold"])
    return cases


def frame(seed=SEED):
    """Every hardship conversation, Mon 6 to Sun 19 September 2027 (480), with the spans the checks read."""
    g = random.Random(seed + 9)
    out, tid = [], FIRST_ID
    for i in range(480):
        f = _new_facts(g)
        if i:
            tid += g.randrange(10, 24)
        day = date(2027, 9, 6) + timedelta(days=i * 14 // 480)
        f.update({"trace_id": f"t-{tid:06d}", "date": day.isoformat(), "source": "September frame"})
        f["documented"] = _documented(f, g)
        f["segment"] = segment(f)
        f["prod"] = production_action(f, g)
        f["tool_error"] = g.random() < 0.05
        f["answered_through_error"] = f["tool_error"] and g.random() < 0.10   # FM-24
        f["wrong_loan_tool"] = f["loans"] > 1 and f["names_loan"] and g.random() < 0.03   # FM-22
        f["approval_sentence"] = f["prod"] != OFFER or g.random() > 0.02    # FM-03 when missing
        f["record_window_months"] = None if not f["relief"] else f["relief"]["end_months_ago"]
        out.append(f)
    return out


if __name__ == "__main__":
    G = gold()
    from collections import Counter
    print(len(G), Counter(c["source"] for c in G))
    print(Counter(c["segment"] for c in G))
    wo = [c for c in G if c["prod"] == OFFER and c["gold"] != OFFER]
    wr = [c for c in G if c["prod"] != OFFER and c["gold"] == OFFER]
    print("wrong offers", len(wo), Counter(c["segment"] for c in wo))
    print("wrongful refusals", len(wr), sum(c["gold"] == OFFER for c in G), Counter(c["segment"] for c in wr))
    F = frame()
    print(len(F), F[0]["trace_id"], F[-1]["trace_id"], Counter(c["segment"] for c in F))
