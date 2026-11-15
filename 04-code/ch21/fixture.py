"""Chapter 21 fixture: the hardship-eligibility judge's trial. SIMULATED.

Nothing here is a live model call. Gold labels stand in for adjudicated officer labels (two readers,
Grace or Ben adjudicating, Chapter 14's operation). Judge verdicts are planted per gold kind so that
Harbor's published counts fall out of real Truss functions; the counts are stated in this file, not
measured from a model. Seed 2026.

Trace IDs: hardship offers between t-185253 and t-229198 whose number ends in 3 or 8, so they cannot
collide with Chapter 18's census (ends in 1 or 6), Chapter 19's canaries and revalidation set, or the
parallel Chapter 20 writer's weekly windows. Candidate replays carry the candidate build in `source`.
"""
import random

SEED = 2026
POS_KINDS = ["window", "stated_work", "income", "wrong_loan", "referral"]
NEG_KINDS = ["ordinary", "anniversary_outside", "stated_correct", "disaster_correct", "two_loans_correct"]

# Held-out trial set (200): kind -> {source: count}
TEST = {
    "window":              {"random": 1, "targeted": 6, "candidate": 7},
    "stated_work":         {"random": 1, "targeted": 6, "candidate": 5},
    "income":              {"random": 0, "targeted": 3, "candidate": 6},
    "wrong_loan":          {"random": 0, "targeted": 0, "candidate": 6},
    "referral":            {"random": 0, "targeted": 3, "candidate": 4},
    "ordinary":            {"random": 100, "targeted": 6, "candidate": 4},
    "anniversary_outside": {"random": 4, "targeted": 4, "candidate": 2},
    "stated_correct":      {"random": 4, "targeted": 6, "candidate": 2},
    "disaster_correct":    {"random": 4, "targeted": 2, "candidate": 2},
    "two_loans_correct":   {"random": 6, "targeted": 4, "candidate": 2},
}
DEV = {
    "window": 7, "stated_work": 6, "income": 5, "wrong_loan": 3, "referral": 3,
    "ordinary": 55, "anniversary_outside": 5, "stated_correct": 6, "disaster_correct": 4,
    "two_loans_correct": 6,
}

# hardship-judge-v1 on the held-out 200: per kind, (wrong verdicts, abstentions, cause of each).
# Positives: wrong verdict = pass on a wrong offer (a miss). Negatives: wrong verdict = false alarm.
V1_TEST = {
    "window": (8, 0, "date_arithmetic"), "stated_work": (5, 1, "stated_vs_record"),
    "income": (3, 0, "income_arithmetic"), "wrong_loan": (0, 0, None), "referral": (2, 0, "policy_rule"),
    "ordinary": (2, 1, "other"), "anniversary_outside": (4, 0, "date_arithmetic"),
    "stated_correct": (4, 0, "stated_vs_record"), "disaster_correct": (1, 0, "policy_rule"),
    "two_loans_correct": (0, 0, None),
}
V1_DEV = {"window": (0, 0), "anniversary_outside": (1, 0)}      # rules were written from dev
# Fix: hardship-judge-v2 (C-03 result + days calculator + two rules drafted from trial failures)
V2_TEST = {"stated_work": (4, 0), "income": (3, 0), "referral": (1, 0),
           "stated_correct": (3, 0), "ordinary": (2, 0)}
# Split, part B: permission-judge-v1 reads the record, C-02/C-03/C-09 results and part A's extraction
JB_TEST = {"stated_work": (5, 0), "income": (4, 0), "window": (1, 0), "referral": (1, 0), "wrong_loan": (1, 0),
           "stated_correct": (3, 0), "ordinary": (2, 0), "disaster_correct": (1, 0)}
# Split, part A: stated-change-judge-v1. Gold positive = the borrower states work or income that
# differs from the account record (stated_work, stated_correct, income kinds).
JA_POS_KINDS = ("stated_work", "stated_correct", "income")
JA_TEST = {"miss": {"stated_work": 1}, "false_alarm": {"ordinary": 2, "disaster_correct": 1}}
# Try It 2: hardship-judge-v1 given the C-03 result as an input, no new rules
V1_C03_TEST = {"window": (1, 0), "stated_work": (5, 1), "income": (3, 0), "referral": (2, 0),
               "ordinary": (2, 1), "stated_correct": (4, 0), "disaster_correct": (1, 0)}

SPANISH = {"miss": 5, "hit": 4, "fa": 4, "tn": 21}     # 34 Spanish traces in the 200
LONG = {"hit": 26, "miss": 3, "fa": 8, "tn": 5}        # conversations over 15 turns


def _ids(rng, n, used):
    out = []
    while len(out) < n:
        k = rng.randrange(185253, 229199)
        if k % 10 not in (3, 8):
            continue
        if any(w <= k <= w + 59 for w in (201251, 205251, 209251, 213251, 217251, 221251)):
            continue                                    # Chapter 19 fresh canary windows
        if 218001 <= k <= 218200:                       # Chapter 19 revalidation set
            continue
        tid = f"t-{k:06d}"
        if tid in used:
            continue
        used.add(tid)
        out.append(tid)
    return out


def _apply(rows, plan, key, order_first=None):
    """Mark verdicts on rows under `key` following plan kind -> (wrong, abstain). Rows inside a kind
    are taken in their stored order, so the order decides which traces carry the misses."""
    for r in rows:
        r[key] = r["gold"]
    by = {}
    for r in rows:
        by.setdefault(r["kind"], []).append(r)
    for kind, spec in plan.items():
        wrong, abstain = spec[0], spec[1]
        rs = by.get(kind, [])
        if order_first:
            rs = sorted(rs, key=order_first(kind))
        for r in rs[:wrong]:
            r[key] = "pass" if r["gold"] == "fail" else "fail"
        for r in rs[wrong:wrong + abstain]:
            r[key] = "cannot_tell"


def build():
    rng = random.Random(SEED)
    used = set()
    test, dev = [], []
    for kind, by_src in TEST.items():
        for src, n in by_src.items():
            for tid in _ids(rng, n, used):
                test.append({"id": tid, "kind": kind, "source": src,
                             "gold": "fail" if kind in POS_KINDS else "pass"})
    for kind, n in DEV.items():
        srcs = ["random"] * n
        if kind in POS_KINDS:
            srcs = ["targeted" if i % 2 == 0 else "candidate" for i in range(n)]
        else:
            srcs = ["random" if i % 4 else "targeted" for i in range(n)]
        for tid, src in zip(_ids(rng, n, used), srcs):
            dev.append({"id": tid, "kind": kind, "source": src,
                        "gold": "fail" if kind in POS_KINDS else "pass"})
    rng.shuffle(test)
    test.sort(key=lambda r: (r["kind"], {"random": 0, "targeted": 1, "candidate": 2}[r["source"]], r["id"]))
    # hardship-judge-v1, held-out: the random window offer is among the misses, the random stated-work
    # offer is caught (sorted so random comes first in window, last in stated_work).
    def v1_order(kind):
        if kind == "stated_work":
            return lambda r: (r["source"] == "random", r["id"])
        return lambda r: (r["source"] != "random", r["id"])
    _apply(test, {k: v[:2] for k, v in V1_TEST.items()}, "v1", v1_order)
    for r in test:
        cause = V1_TEST[r["kind"]][2]
        r["cause"] = cause if r["v1"] != r["gold"] else None
    _apply(dev, V1_DEV, "v1")
    _apply(test, V2_TEST, "v2")
    _apply(test, JB_TEST, "jb")
    _apply(test, V1_C03_TEST, "v1_c03")
    for r in test:
        r["ja_gold"] = "fail" if r["kind"] in JA_POS_KINDS else "pass"
        r["ja"] = r["ja_gold"]
    for kind, n in JA_TEST["miss"].items():
        for r in [x for x in test if x["kind"] == kind][-n:]:
            r["ja"] = "pass"
    for kind, n in JA_TEST["false_alarm"].items():
        for r in [x for x in test if x["kind"] == kind][-n:]:
            r["ja"] = "fail"
    # Spanish and long-conversation flags, planted by cell of the v1 confusion
    cells = {"hit": [], "miss": [], "fa": [], "tn": []}
    for r in test:
        if r["gold"] == "fail":
            cells["hit" if r["v1"] == "fail" else "miss"].append(r)
        else:
            cells["fa" if r["v1"] != "pass" else "tn"].append(r)
    rng2 = random.Random(SEED + 21)
    for cell, rs in cells.items():
        order = rs[:]
        rng2.shuffle(order)
        for i, r in enumerate(order):
            r["lang"] = "es" if i < SPANISH[cell] else "en"
        rng2.shuffle(order)
        for i, r in enumerate(order):
            r["long"] = i < LONG[cell]
    return dev, test


# Construct-validity edits on 40 held-out ordinary offers that hardship-judge-v1 passed.
# Preserving edits: reword the borrower's message, reorder two turns, add a Spanish courtesy phrase.
# Changing edits (ten each): relief end date moved inside the window; borrower states self-employment;
# offer moved to the loan the borrower did not name; record shows three payments behind.
EDIT_TYPES = ["date", "stated", "loan", "arrears"]
CHANGED_V1 = {"date": 2, "stated": 1, "loan": 8, "arrears": 4}
CHANGED_JB = {"date": 10, "stated": 3, "loan": 10, "arrears": 10}
PRESERVED_UNCHANGED = 38


def construct_edits():
    base = ["pass"] * 40
    preserved = ["pass"] * PRESERVED_UNCHANGED + ["fail"] * (40 - PRESERVED_UNCHANGED)
    types = [t for t in EDIT_TYPES for _ in range(10)]
    def changed(plan):
        out = []
        for t in EDIT_TYPES:
            out += ["fail"] * plan[t] + ["pass"] * (10 - plan[t])
        return out
    return base, preserved, types, changed(CHANGED_V1), changed(CHANGED_JB)
