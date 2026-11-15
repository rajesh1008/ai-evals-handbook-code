"""SIMULATED November 2027 fee traffic and a stand-in for fee-judge-v1.

Seed 2026. Reader gold and judge verdicts are planted from documented rates;
no model is called. The statistical work in truss.reportcard is real.
"""
from __future__ import annotations

import random
from collections import Counter

SEED = 2026
N_JUDGED = 2400
N_LABELED = 300
# Production fee traces after the 4-17 October fortnight. All-flow IDs run
# onwards from t-185251; fee conversations take every fifth ID so other flows
# keep their space (approximate 21.5% fee share).
FIRST_ID = 185251
ID_STEP = 5

# Production kind mix, late October to early November 2027, after months of
# fee-path fixes. Residual fails sit near 1.7%, not the 9.0% of the Chapter 16
# development fixture (that fixture was enriched so a TPR could be measured).
PROD_KINDS = [
    ("right_no", 0.575, False),
    ("right_waive", 0.318, False),
    ("defer_review", 0.048, False),
    ("defer_tool", 0.042, False),
    ("fail_amount", 0.007, True),
    ("fail_window", 0.005, True),
    ("fail_loan", 0.003, True),
    ("fail_invent", 0.002, True),
]

# Chapter 16 development mix (ledger): 27 fails in 100, kinds from the
# enriched October fortnight. Used only to build the look-alike injection.
DEV_KIND_SHARES = {
    # Chapter 16 development set was stratified: 27 fails in 100, not the
    # raw fortnight mix (about 9%). The rubric examples were written from
    # that enriched 100, so a look-alike validation set should match it.
    "right_no": 0.40,
    "right_waive": 0.24,
    "defer_review": 0.05,
    "defer_tool": 0.04,
    "fail_invent": 0.07,
    "fail_amount": 0.07,
    "fail_window": 0.06,
    "fail_loan": 0.05,
    "tool_bug": 0.02,
}

# Judge miss rates (share of true fails marked pass) and false-alarm rates
# (share of true passes marked fail). The stand-in under-calls overall: it
# misses more than it invents, especially on Spanish traces and on window
# arithmetic that was not in the rubric examples.
MISS = {
    # (kind, lang): miss rate
    ("fail_amount", "en"): 0.28,
    ("fail_amount", "es"): 0.52,
    ("fail_window", "en"): 0.38,
    ("fail_window", "es"): 0.62,
    ("fail_loan", "en"): 0.22,
    ("fail_loan", "es"): 0.48,
    ("fail_invent", "en"): 0.18,
    ("fail_invent", "es"): 0.40,
}
FALSE_ALARM = {
    ("right_no", "en"): 0.0010,
    ("right_no", "es"): 0.0030,
    ("right_waive", "en"): 0.0012,
    ("right_waive", "es"): 0.0035,
    ("defer_review", "en"): 0.0060,
    ("defer_review", "es"): 0.0140,
    ("defer_tool", "en"): 0.0060,
    ("defer_tool", "es"): 0.0140,
    ("tool_bug", "en"): 0.0000,  # v1.1: matching a wrong tool is still a pass
    ("tool_bug", "es"): 0.0000,
}

SPANISH_SHARE = 0.125
LONG_SHARE = 0.30  # replies at or above 140 words; length is not what MC-02 reads


def _pick_kind(rng, table):
    r = rng.random()
    acc = 0.0
    for kind, share, is_fail in table:
        acc += share
        if r <= acc:
            return kind, is_fail
    kind, share, is_fail = table[-1]
    return kind, is_fail


def _judge_verdict(rng, kind, is_fail, lang):
    if is_fail:
        miss = MISS.get((kind, lang), 0.35)
        return "pass" if rng.random() < miss else "fail"
    fa = FALSE_ALARM.get((kind, lang), 0.002)
    return "fail" if rng.random() < fa else "pass"


def _length_bin(rng):
    return "long" if rng.random() < LONG_SHARE else "short"


def build_production(n=N_JUDGED, seed=SEED):
    rng = random.Random(seed)
    traces = []
    for i in range(n):
        kind, is_fail = _pick_kind(rng, PROD_KINDS)
        lang = "es" if rng.random() < SPANISH_SHARE else "en"
        gold = "fail" if is_fail else "pass"
        judge = _judge_verdict(rng, kind, is_fail, lang)
        tid = f"t-{FIRST_ID + i * ID_STEP:06d}"
        traces.append({
            "trace_id": tid,
            "kind": kind,
            "lang": lang,
            "length": _length_bin(rng),
            "gold": gold,
            "judge": judge,
        })
    return traces


def draw_labeled(traces, n=N_LABELED, seed=SEED):
    """A simple random sample of `n` traces. These enter the rate and PPI."""
    rng = random.Random(seed + 1)
    idx = list(range(len(traces)))
    rng.shuffle(idx)
    take = sorted(idx[:n])
    labeled = [traces[i] for i in take]
    unlabeled_only = [traces[i] for i in range(len(traces)) if i not in set(take)]
    return labeled, unlabeled_only


def reserved_dev_ids():
    """Chapter 16 development set lived inside t-177401..t-185250. We keep a
    synthetic reserved list of 100 IDs in that range so a leak check has
    something to compare against; none of this chapter's production IDs overlap.
    """
    rng = random.Random(SEED + 2)
    return [f"t-{rng.randint(177401, 185250)}" for _ in range(100)]


def reserved_dev_kinds(n=100, seed=SEED):
    """A 100-trace development kind list matching Chapter 16's enriched mix."""
    rng = random.Random(seed + 3)
    items = list(DEV_KIND_SHARES.items())
    kinds = []
    for _ in range(n):
        r = rng.random()
        acc = 0.0
        chosen = items[-1][0]
        for k, share in items:
            acc += share
            if r <= acc:
                chosen = k
                break
        kinds.append(chosen)
    return kinds


def describe(traces):
    n = len(traces)
    gold_fail = sum(t["gold"] == "fail" for t in traces)
    judge_fail = sum(t["judge"] == "fail" for t in traces)
    langs = Counter(t["lang"] for t in traces)
    kinds = Counter(t["kind"] for t in traces)
    return {
        "n": n,
        "first": traces[0]["trace_id"] if traces else None,
        "last": traces[-1]["trace_id"] if traces else None,
        "gold_fail": gold_fail,
        "gold_rate": gold_fail / n if n else None,
        "judge_fail": judge_fail,
        "judge_rate": judge_fail / n if n else None,
        "lang": dict(langs),
        "kinds": dict(kinds),
    }


def confusion_counts(rows):
    tp = fn = fp = tn = 0
    for r in rows:
        if r["gold"] == "fail" and r["judge"] == "fail":
            tp += 1
        elif r["gold"] == "fail" and r["judge"] == "pass":
            fn += 1
        elif r["gold"] == "pass" and r["judge"] == "fail":
            fp += 1
        else:
            tn += 1
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(rows)}
