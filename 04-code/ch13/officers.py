"""Simulated loan officers. SIMULATED: no human labelled these traces.

Each reader applies the guideline revision in force through a reading function, then slips with a
probability that rises after 45 minutes in a sitting. The readings that differ are the ones the chapter
describes; nothing else differs between the two readers.

  revision 1  "the borrower has stated their monthly income": Ben reads income as gross pay and asks for
              it when only take-home pay is given; Grace counts take-home pay
  revisions 1-2  "had a deferral or extension on this loan in the last twelve months": Grace counts from the
              date the relief ended (the policy's reading), Ben from the date it was granted
  all         both treat a disaster forbearance as outside the window, as branch practice does, whatever
              the written policy says
  drift       from Mon 26 July 2027 Ben slips back to asking for gross pay on take-home traces (p = 0.5)
"""
import math
import random

from fixture import LABELS, decide

BASE_SLIP = 0.02


def slip_p(minute):
    return BASE_SLIP + max(0.0, minute - 45) * 0.0025


def intended(name, t, revision, day):
    take_home = not (name == "ben" and revision == "r1")
    if name == "ben" and day >= "2027-07-26" and t["income_basis"] == "take_home":
        take_home = False if random.Random(f"drift{t['trace_id']}{day}").random() < 0.5 else take_home
    window_from = "start" if (name == "ben" and revision in ("r1", "r2")) else "end"
    g = random.Random(f"{name}{t['trace_id']}")
    unclear = g.random() < 0.5  # an unclear loan reference: each reader guesses
    t2 = t
    if t["relief"] and t["relief"].get("end_missing") and revision != "draft" and g.random() < 0.5:
        return "cannot_tell"
    if t["relief"] and t["relief"].get("end_missing"):
        t2 = dict(t, relief=dict(t["relief"], end_months_ago=t["relief"]["start_months_ago"] - g.choice([1, 3, 6])))
    return decide(t2, disaster_counts=False, take_home_counts=take_home, window_from=window_from, unclear_is_named=unclear)


def minutes_for(name, t, g, learning=False, reread=False):
    med = (3.0 if learning else 1.6 if reread else 2.2) * (1.12 if t["lang"] == "es" and name == "ben" else 1.0)
    return round(math.exp(math.log(med) + g.gauss(0, 0.28)), 2)


def read(name, t, revision, day, minute, g):
    lab = intended(name, t, revision, day)
    if g.random() < slip_p(minute):
        lab = g.choice([x for x in LABELS if x != lab])
    reason = {"decline_window": "relief inside 12 months", "ask_income": "no usable income",
              "ask_which_loan": "loan not named", "refer_to_officer": "self-employed or 3+ behind",
              "draft_deferral": "eligible"}.get(lab, "")
    pq = bool(t["relief"] and t["relief"]["kind"] == "disaster" and t["relief"]["end_months_ago"] < 12 and g.random() < 0.5)
    return lab, reason, pq
