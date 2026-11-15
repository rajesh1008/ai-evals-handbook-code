"""SIMULATED annotators for Chapter 14. Nothing here is a measurement of people. Each reader's label is the
policy's answer under that reader's reading of the guideline, plus slips. Every parameter is stated here.

  Readers     marisol (loan officer, Tucson, bilingual), daniel (loan officer, Henderson), kevin (data
              scientist). Hours a week: 6, 6, 3.
  Habits      officers: "within a year" on the anniversary case while the guideline is silent (p 0.9);
              kevin: the employment on file over the borrower's statement while the guideline is silent (p 0.8).
              After a sentence is added the habit persists at p 0.12 in its first week and 0.04 after.
  Slips       base 0.080 marisol, 0.085 daniel, 0.065 kevin; times 1.0, 0.85, 0.7, 0.65, 0.65 by week;
              times 2.5 for daniel and 1.8 for kevin on Spanish traces; times 1.8 after 45 minutes in a sitting.
  Minutes     log-normal, median officers 5.6, 4.6, 4.0, 3.7, 3.6 and kevin 4.4, 3.9, 3.5, 3.3, 3.2 by week;
              times 1.2 with relief history or two loans; times 1.35 on Spanish traces for daniel and kevin;
              sigma 0.35.
  Edge facts  unclear loan reference read correctly at p 0.92 (G-04 has it); a missing end date gives
              cannot_tell at p 0.85.
"""
import math
import random

import fixture as F
import guideline as G

READERS = ("marisol", "daniel", "kevin")
OFFICERS = ("marisol", "daniel")
HOURS = {"marisol": 6.0, "daniel": 6.0, "kevin": 3.0}
RATE = {"marisol": 60.0, "daniel": 60.0, "kevin": 85.0, "adjudicator": 60.0, "diane": 95.0}
BASE = {"marisol": 0.080, "daniel": 0.085, "kevin": 0.065}
LEARN = [1.0, 0.85, 0.7, 0.65, 0.65]
MED = {"officer": [5.6, 4.6, 4.0, 3.7, 3.6], "kevin": [4.4, 3.9, 3.5, 3.3, 3.2]}
NEAR = {"ask_which_loan": ["ask_income", "draft_deferral"], "ask_income": ["ask_which_loan", "draft_deferral"],
        "decline_window": ["draft_deferral", "refer_to_officer"], "refer_to_officer": ["draft_deferral", "decline_window"],
        "draft_deferral": ["refer_to_officer", "decline_window"], "cannot_tell": ["decline_window", "draft_deferral"]}


def habit_p(version, what, weeks_since_change):
    if not G.has(version, what):
        return {"anniversary": 0.9, "stated_work": 0.8}[what]
    return 0.12 if weeks_since_change == 0 else 0.04


def intended(reader, t, version, weeks_since, g):
    """The label this reader means to give, and why (correct | habit | guess)."""
    f = t["facts"]
    anniv_in = reader in OFFICERS and F.is_anniversary(f) and g.random() < habit_p(version, "anniversary", weeks_since)
    record = reader == "kevin" and F.is_stated_work(f) and g.random() < habit_p(version, "stated_work", weeks_since)
    unclear_named = f["loan_unclear"] and g.random() > 0.92
    lab = F.required(f, anniversary_inside=anniv_in, use_record=record, unclear_is_named=unclear_named)
    if lab == "cannot_tell" and g.random() > 0.85:
        lab = "decline_window"
    why = "correct" if lab == t["required"] else ("habit" if (anniv_in or record) else "guess")
    return lab, why


def read(reader, t, version, week, weeks_since, minute_in_sitting, g):
    lab, why = intended(reader, t, version, weeks_since, g)
    p = BASE[reader] * LEARN[week - 1]
    if t["facts"]["lang"] == "es":
        p *= {"daniel": 2.5, "kevin": 1.8}.get(reader, 1.0)
    if minute_in_sitting > 45:
        p *= 1.8
    if g.random() < p:
        lab, why = g.choice(NEAR[lab]), "slip"
    return lab, why


def minutes(reader, t, week, g):
    med = (MED["kevin"] if reader == "kevin" else MED["officer"])[week - 1]
    f = t["facts"]
    if f["relief"] or f["loans"] > 1:
        med *= 1.2
    if f["lang"] == "es" and reader != "marisol":
        med *= 1.35
    return med * math.exp(g.gauss(0, 0.35))
