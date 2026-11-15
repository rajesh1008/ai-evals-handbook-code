"""Compute CIs, power n, Signature 7 wall for Chapter 31."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.stats import (
    wilson_ci, clopper_upper, n_for_upper_bound, n_for_margin,
    paired_bootstrap_diff, unpaired_rate_diff, holm_adjust, bonferroni_alpha,
    stratified_rates, risk_diff_effect, signature7_wall, permutation_p_paired,
)

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
board = FIX["board"]
k = sum(1 for x in board if x["fail"])
n = len(board)
ci = wilson_ci(k, n)
up = clopper_upper(k, n)
n0 = n_for_upper_bound(FIX["target_hardship"], failures=0)
n_margin = n_for_margin(0.005, 0.002)
strat = stratified_rates(board, fail_key="fail")
base = [p["baseline_pass"] for p in FIX["paired"]]
cand = [p["candidate_pass"] for p in FIX["paired"]]
paired = paired_bootstrap_diff(base, cand)
unpaired = unpaired_rate_diff(base, cand)
# Unpaired injection view: reshuffle into two groups of 200 (SIMULATED misleading)
import random
rng = random.Random(2031)
pool = base + cand
rng.shuffle(pool)
g1, g2 = pool[:200], pool[200:]
unpaired_inject = unpaired_rate_diff(g1, g2)
perm = permutation_p_paired(base, cand)
holm = holm_adjust(FIX["raw_p_values"])
wall = signature7_wall([
    {"claim": "0.5% upper bound with zero failures", "kind": "zero_fail_upper", "target": 0.005},
    {"claim": "estimate ~0.5% rate ±0.2 pp", "kind": "margin", "p": 0.005, "margin": 0.002},
    {"claim": "Victor board hardship set", "kind": "fixed", "n": 2400},
    {"claim": "2% fee upper bound zero fail", "kind": "zero_fail_upper", "target": 0.02},
    {"claim": "Is 2% on 100 real? (n=100 toy)", "kind": "fixed", "n": 100},
])
effect = risk_diff_effect(paired["baseline_rate"], paired["candidate_rate"])
out = {
    "kind": "SIMULATED",
    "digest": FIX["digest"],
    "board_ci": ci,
    "board_upper": up,
    "n_zero_fail_for_0_5pct": n0,
    "n_margin_0_5pct_pm_0_2pp": n_margin,
    "stratified": strat,
    "paired": paired,
    "unpaired_paired_labels": unpaired,
    "unpaired_injection": unpaired_inject,
    "permutation": perm,
    "holm": holm,
    "bonferroni_alpha_05_m8": bonferroni_alpha(0.05, 8),
    "signature7": wall,
    "effect": effect,
    "victor_n": 2400,
}
(OUT / "lab.json").write_text(json.dumps(out, indent=2))
print(json.dumps({
    "k": k, "n": n, "rate": ci["rate"], "wilson": [ci["lo"], ci["hi"]],
    "upper": up["upper"], "n0": n0, "n_margin": n_margin,
    "paired_diff": paired["point_diff"], "paired_CI": [paired["lo"], paired["hi"]],
    "paired_includes_zero": paired["includes_zero"],
    "unpaired_inject_diff": unpaired_inject["diff"],
    "perm_p": perm["p"],
}, indent=2))
