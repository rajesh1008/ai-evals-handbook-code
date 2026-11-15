"""Chapter 12 fixture: Harbor Lending's golden set v1.0 (assembled Mon 7 June 2027) and the book's
simulator for what Compass does on it.

SIMULATED. Case features, labels and verdicts are drawn from planted rates (stated below) with seed
2026; the turn counts of production hardship cases come from the pilot fixture database. Nothing
here is a model output. The real model runs of this chapter are synth.py and leak.py.
"""
import random, sqlite3
from math import exp
from pathlib import Path

SEED = 2026
DB = Path(__file__).resolve().parents[1] / "truss/fixtures/compass_pilot.db"
FLOWS = ("account_question", "statement_request", "fee_explanation", "payoff_letter", "lien_release", "hardship")
# (source, flow): count. Production = frozen 300 (Ch2) + March fee draw 200 (Ch8) + weekly draws 457.
COUNTS = {
    "production": {"account_question": 120, "statement_request": 70, "fee_explanation": 270,
                   "payoff_letter": 150, "lien_release": 85, "hardship": 262},
    "incident":   {"account_question": 6, "statement_request": 5, "fee_explanation": 45,
                   "payoff_letter": 30, "lien_release": 15, "hardship": 52},
    "authored":   {"account_question": 10, "fee_explanation": 10, "payoff_letter": 24,
                   "lien_release": 10, "hardship": 26},
    "planted":    {"fee_explanation": 10},
}
SLICE_MIX = {   # planted slice shares by source
    "production": {"common": .78, "uncommon": .13, "hard": .07, "adversarial": .01, "ood": .01},
    "incident":   {"common": .05, "uncommon": .25, "hard": .45, "adversarial": .15, "ood": .10},
    "authored":   {"hard": .45, "adversarial": .40, "ood": .15},
    "planted":    {"hard": 1.0},
}
# planted hardship feature rates in production (the book's Harbor), and in officer-authored cases
HARDSHIP_PROD = {"two_loans": .14, "prior_relief": .22, "edge": .07, "spanish": .09, "tool_error": .03,
                 "self_employed": .12, "income_missing": .61}
HARDSHIP_AUTH = {"two_loans": .50, "prior_relief": .35, "edge": .12, "spanish": .0, "tool_error": .0,
                 "self_employed": .08, "income_missing": .15}
# the simulator's per-slice pass rates for two builds (planted)
PASS = {"production": {"common": .975, "uncommon": .93, "hard": .80, "adversarial": .78, "ood": .85},
        "rc-0611-1":  {"common": .99, "uncommon": .95, "hard": .84, "adversarial": .62, "ood": .86}}


def pick(g, mix):
    r, acc = g.random(), 0.0
    for k, p in mix.items():
        acc += p
        if r < acc:
            return k
    return k


def hardship_turns():
    return [t for (t,) in sqlite3.connect(DB).execute("select turns from traces where flow='hardship' order by trace_id")]


def features(g, rates, turns_pool=None, authored=False):
    f = {k: g.random() < p for k, p in rates.items() if k not in ("edge", "prior_relief")}
    f["prior_relief"] = g.random() < rates["prior_relief"]
    f["edge"] = f["prior_relief"] and g.random() < rates["edge"] / rates["prior_relief"]
    f["turns"] = g.choice(turns_pool) if turns_pool else max(3, int(g.gauss(6, 1.5)))
    return f


def fail_prob(f):
    """The simulator's hardship failure model (planted): logistic in the case's features."""
    z = (-3.2 + 1.2 * f.get("two_loans", 0) + 1.1 * f.get("edge", 0) + 0.5 * f.get("prior_relief", 0)
         + 0.7 * f.get("spanish", 0) + 1.5 * f.get("tool_error", 0) + 0.8 * f.get("self_employed", 0)
         + 0.5 * f.get("income_missing", 0) + 0.06 * (f.get("turns", 8) - 8))
    return 1 / (1 + exp(-z))


def build(seed=SEED):
    g = random.Random(seed)
    turns = hardship_turns()
    cases, i = [], 0
    for source, flows in COUNTS.items():
        for flow, n in flows.items():
            for _ in range(n):
                i += 1
                c = {"case_id": f"g-{i:04d}", "trace_id": f"t-{g.randrange(1, 108195):06d}", "flow": flow,
                     "source": source, "slice": pick(g, SLICE_MIX[source]), "planted": source == "planted",
                     "split": "regression", "policy_version": "HP-2027-04" if flow == "hardship" else "FS-2026-03",
                     "labelled_by": "officer" if flow == "hardship" else "Ryan",
                     "labelled_on": f"2027-{g.choice(['01','02','03','03','04','05']) }-{g.randrange(1, 29):02d}",
                     "label": "pass", "features": {}}
                if source == "authored":
                    c["trace_id"] = None
                if flow == "hardship":
                    rates = HARDSHIP_AUTH if source == "authored" else HARDSHIP_PROD
                    c["features"] = features(g, rates, None if source == "authored" else turns)
                    if c["features"]["edge"] and c["slice"] == "common":
                        c["slice"] = "hard"
                cases.append(c)
    return cases


def verdicts(cases, build_name, seed=SEED):
    """Simulated pass/fail per case for a build, from the planted per-slice pass rates."""
    g = random.Random(f"{seed}-{build_name}")
    return {c["case_id"]: g.random() < PASS.get(build_name, PASS["production"])[c["slice"]] for c in cases}
