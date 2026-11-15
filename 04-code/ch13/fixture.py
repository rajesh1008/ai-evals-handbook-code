"""Chapter 13 fixture: 300 hardship traces for the expert gold set. SIMULATED.

262 are the rate-eligible production hardship cases of harbor-golden v1.1 (Chapter 12); 38 are hardship
traces from Thu 1 to Fri 9 July 2027 (IDs t-123104 onward, a range this chapter chose and logs). The
facts on each trace are generated (seed 2026); Compass's reply is generated from the facts with planted
errors. Two right answers are computed, never shown to anyone in the story:
  text_action   HP-2027-04 as written (a disaster forbearance is a deferral, so it counts in the window;
                a take-home figure counts as a stated income only if the policy is read that way, see below)
  final_action  HP-2027-04 with bulletin HB-2027-07 (Thu 15 July 2027): disaster forbearance does not
                count in the window; any stated monthly figure, gross or take-home, is a stated income
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "ch12"))
from policy import ACTIONS  # noqa: E402

SEED = 2026
FIRST_JULY_ID = 123104
LABELS = ACTIONS  # ask_which_loan, ask_income, decline_window, refer_to_officer, draft_deferral


def _facts(g):
    two = g.random() < 0.20
    f = {"loans": 2 if two else 1, "names_loan": (not two) or g.random() < 0.55,
         "income_basis": g.choices(["gross", "take_home", "none"], [0.52, 0.30, 0.18])[0],
         "self_employed": g.random() < 0.11, "behind": g.choices([0, 1, 2, 3, 4], [0.38, 0.30, 0.18, 0.09, 0.05])[0],
         "lang": "es" if g.random() < 0.14 else "en"}
    f["loan_unclear"] = two and f["names_loan"] and g.random() < 0.25
    f["income"] = None if f["income_basis"] == "none" else g.randrange(1800, 6400, 50)
    r = g.random()
    if r < 0.58:
        f["relief"] = None
    else:
        kind = g.choices(["deferral", "extension", "disaster"], [0.50, 0.36, 0.14])[0]
        dur = {"deferral": g.choice([3, 6, 6, 9, 12]), "extension": g.choice([1, 2, 2, 3]), "disaster": g.choice([3, 6])}[kind]
        end = g.choice([2, 4, 6, 8, 9, 10, 11, 11, 13, 15, 18, 24])
        f["relief"] = {"kind": kind, "start_months_ago": end + dur, "end_months_ago": end,
                       "end_missing": g.random() < 0.04}
    return f


def decide(f, *, disaster_counts, take_home_counts=True, window_from="end", unclear_is_named=False):
    """HP-2027-04's first-reply action. The keyword arguments are the readings in dispute. A loan
    reference that fits both loans ("the car loan" when both are auto loans) is not a named loan."""
    if f["loans"] > 1 and (not f["names_loan"] or (f.get("loan_unclear") and not unclear_is_named)):
        return "ask_which_loan"
    if f["income_basis"] == "none" or (f["income_basis"] == "take_home" and not take_home_counts):
        return "ask_income"
    rel = f["relief"]
    if rel and (rel["kind"] != "disaster" or disaster_counts):
        months = rel["end_months_ago"] if window_from == "end" else rel["start_months_ago"]
        if months < 12:
            return "decline_window"
    if f["self_employed"] or f["behind"] >= 3:
        return "refer_to_officer"
    return "draft_deferral"


REASON = {"ask_which_loan": "which loan the hardship concerns", "ask_income": "the monthly income",
          "decline_window": "relief on this loan ended fewer than 12 calendar months ago",
          "refer_to_officer": "a loan officer needs to review the account", "draft_deferral": "a deferral can be drafted"}


def _reply(f, action, g):
    """Compass's reply for the action it took, with the explanation claims a reader checks."""
    claims = {"next_step": True, "reason": True, "approval_sentence": action == "draft_deferral"}
    parts = {
        "ask_which_loan": "Which of your two loans is this about?",
        "ask_income": "To look at options, what is your current monthly income?",
        "decline_window": "Because relief on this loan ended fewer than 12 calendar months ago, I can't draft a deferral. "
                          "I can set up a call with a loan officer.",
        "refer_to_officer": "A loan officer will review your account and call you within two business days.",
        "draft_deferral": "I've drafted a three-month deferral for you."}
    text = parts[action]
    if action in ("decline_window", "refer_to_officer") and g.random() < 0.10:
        text = text.replace("ended fewer than 12 calendar months ago", "was granted in the last year") \
            .replace("will review your account", "will review your income documents")
        claims["reason"] = False
    if action == "draft_deferral":
        if g.random() < 0.04:
            claims["approval_sentence"] = False
        else:
            text += " A loan officer must approve it before it takes effect."
        if g.random() < 0.06:
            text += " You'll owe nothing until it ends."
            claims["next_step"] = False
    return text, claims


def build(seed=SEED):
    g = random.Random(seed)
    golden = random.Random(seed + 1).sample(range(1, 108195), 262)
    traces = []
    for i in range(300):
        f = _facts(g)
        if i < 262:
            tid, src = f"t-{golden[i]:06d}", "harbor-golden v1.1"
            day = date(2027, 1, 4) + timedelta(days=g.randrange(0, 177))
        else:
            tid, src = f"t-{FIRST_JULY_ID + (i - 262) * 241 + g.randrange(0, 200):06d}", "July production"
            day = date(2027, 7, 1) + timedelta(days=(i - 262) * 8 // 38)
        f.update({"trace_id": tid, "source": src, "date": day.isoformat()})
        f["text_action"] = decide(f, disaster_counts=True)
        f["final_action"] = decide(f, disaster_counts=False)
        if f["relief"] and f["relief"]["end_missing"] and f["final_action"] in ("decline_window", "draft_deferral", "refer_to_officer"):
            f["final_action"] = "cannot_tell"  # the window turns on a date the trace does not show
        right = f["final_action"]
        right = right if right != "cannot_tell" else "refer_to_officer"
        compass = right if g.random() < 0.93 else g.choice([a for a in LABELS if a != right])
        f["compass_action"] = compass
        f["reply"], f["claims"] = _reply(f, compass, g)
        traces.append(f)
    traces.sort(key=lambda t: (t["date"], t["trace_id"]))
    return traces


def render(t):
    """What the officer sees in the labelling screen: the facts as the tools returned them, the
    borrower's message and Compass's reply. No label, no other reader."""
    loans = "two loans" if t["loans"] == 2 else "one loan"
    inc = ("gives no income figure" if t["income_basis"] == "none" else f"says gross monthly pay is ${t['income']:,}"
           if t["income_basis"] == "gross" else f"says take-home pay is ${t['income']:,} a month")
    rel = "no prior relief on record"
    if t["relief"]:
        r = t["relief"]
        rel = (f"prior {r['kind'].replace('disaster', 'disaster forbearance')}: started {r['start_months_ago']} months ago, "
               + ("end date not shown" if r.get("end_missing") else f"ended {r['end_months_ago']} months ago"))
    who = "self-employed" if t["self_employed"] else "employed"
    named = "" if t["loans"] == 1 else (" (both auto loans; borrower says 'the car loan')" if t.get("loan_unclear") else
                                         " (names the loan)" if t["names_loan"] else " (does not say which loan)")
    return (f"{t['trace_id']} {t['date']} [{t['lang']}]\nAccount: {loans}{named}; {t['behind']} payments behind; {rel}\n"
            f"Borrower: lost hours at work, {who}, {inc}\nCompass: {t['reply']}")
