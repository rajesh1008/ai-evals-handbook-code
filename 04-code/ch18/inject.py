"""Failure injection: a validation set drawn from the Chapter 16 development
kind mix (the distribution of the rubric examples), not from production.

The stand-in judge is more accurate on those familiar kinds, because that is
what the prompt was tuned on. The injected set therefore reports an optimistic
kappa and would, if used alone, look like a report card.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import (
    DEV_KIND_SHARES, SEED, MISS, FALSE_ALARM, SPANISH_SHARE, _length_bin,
    reserved_dev_kinds, describe, confusion_counts,
)
from truss.reportcard import (
    kappa_interval, total_variation, kind_mix, as_indicator, ppi_interval,
    build_card, admit_decide,
)
from truss.judge import confusion, rates

# On familiar (rubric) kinds the stand-in misses far less than it does on
# residual production fails. That is the point of the injection: the prompt
# was tuned against these kinds.
FAMILIAR_MISS = {
    ("fail_amount", "en"): 0.06,
    ("fail_amount", "es"): 0.12,
    ("fail_window", "en"): 0.08,
    ("fail_window", "es"): 0.14,
    ("fail_loan", "en"): 0.05,
    ("fail_loan", "es"): 0.10,
    ("fail_invent", "en"): 0.04,
    ("fail_invent", "es"): 0.10,
}
FAMILIAR_FA = {
    ("right_no", "en"): 0.004,
    ("right_no", "es"): 0.008,
    ("right_waive", "en"): 0.004,
    ("right_waive", "es"): 0.008,
    ("defer_review", "en"): 0.010,
    ("defer_review", "es"): 0.020,
    ("defer_tool", "en"): 0.010,
    ("defer_tool", "es"): 0.020,
    ("tool_bug", "en"): 0.000,
    ("tool_bug", "es"): 0.000,
}

FAIL_KINDS = {"fail_amount", "fail_window", "fail_loan", "fail_invent"}


def _pick(rng, shares):
    r = rng.random()
    acc = 0.0
    items = list(shares.items())
    for k, share in items:
        acc += share
        if r <= acc:
            return k
    return items[-1][0]


def build_lookalike(n=200, seed=SEED + 17):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        kind = _pick(rng, DEV_KIND_SHARES)
        lang = "es" if rng.random() < SPANISH_SHARE else "en"
        gold = "fail" if kind in FAIL_KINDS else "pass"
        if gold == "fail":
            miss = FAMILIAR_MISS.get((kind, lang), 0.08)
            judge = "pass" if rng.random() < miss else "fail"
        else:
            fa = FAMILIAR_FA.get((kind, lang), 0.005)
            judge = "fail" if rng.random() < fa else "pass"
        rows.append({
            "trace_id": f"look-{i:04d}",
            "kind": kind, "lang": lang, "length": _length_bin(rng),
            "gold": gold, "judge": judge,
        })
    return rows


def pct(x):
    return "nan" if x != x else f"{100 * x:.2f}%"


def main():
    rows = build_lookalike()
    gold = [r["gold"] for r in rows]
    judge = [r["judge"] for r in rows]
    d = describe(rows)
    cm = confusion(gold, judge)
    rt = rates(cm)
    kap = kappa_interval(gold, judge, n_boot=2000, seed=SEED)
    tv = total_variation(kind_mix(r["kind"] for r in rows), kind_mix(reserved_dev_kinds()))
    print("=" * 100)
    print("INJECTION: 200-trace validation set drawn from the Ch16 development kind mix")
    print("=" * 100)
    print(f"gold fails {d['gold_fail']}/{d['n']} = {pct(d['gold_rate'])}  "
          f"(production is near 1.7%; this set is near the 27% dev fail share)")
    print(f"judge fails {d['judge_fail']}/{d['n']} = {pct(d['judge_rate'])}")
    print(f"kinds: {d['kinds']}")
    print(f"confusion TP {cm['tp']} FN {cm['fn']} FP {cm['fp']} TN {cm['tn']}")
    print(f"TPR {pct(rt['tpr'])}  TNR {pct(rt['tnr'])}")
    print(f"kappa {kap['kappa']:.4f}  interval {kap['ci'][0]:.4f} to {kap['ci'][1]:.4f}")
    print(f"TV against reserved development mix {tv:.4f}  (near 0 = look-alike)")
    # A card built only on this set must refuse: the mix clones the reserved set.
    # Use the look-alike rows as both labelled and "unlabelled" so admission
    # sees the cloned mix.
    card = build_card(
        gold, judge, judge,
        judge="fee-judge-v1", metric_card="MC-02 v1.1",
        segments=[r["lang"] for r in rows],
        val_ids=[r["trace_id"] for r in rows],
        reserved_ids=["dev-x"],  # no ID leak; the refusal must come from the mix
        val_kinds=[r["kind"] for r in rows],
        reserved_kinds=reserved_dev_kinds(),
        invariance_key=[r["length"] for r in rows],
        n_boot=500, seed=SEED,
    )
    decision = admit_decide(card)
    print(f"admit {decision['admit']}  role {decision['role']}")
    print(f"reasons: {decision['reasons']}")
    out = {
        "n": d["n"], "gold_fail": d["gold_fail"], "gold_rate": d["gold_rate"],
        "judge_fail": d["judge_fail"], "judge_rate": d["judge_rate"],
        "kinds": d["kinds"], "cm": cm, "tpr": rt["tpr"], "tnr": rt["tnr"],
        "tpr_ci": rt["tpr_ci"], "tnr_ci": rt["tnr_ci"],
        "kappa": kap["kappa"], "kappa_ci": kap["ci"], "kind_tv": tv,
        "admit": decision["admit"], "role": decision["role"],
        "reasons": decision["reasons"],
    }
    (HERE / "out" / "inject.json").write_text(json.dumps(out, indent=2, default=str))
    print("wrote", HERE / "out" / "inject.json")


if __name__ == "__main__":
    main()
