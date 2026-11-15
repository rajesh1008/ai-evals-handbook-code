"""Chapter 20 Try It Yourself variations (SIMULATED decisions; Truss computations real).

1. Measure ECE five ways on the same January scores: the number moves with the protocol.
2. Route on the verbalised confidence instead of the log-probability.
3. Route on the judge-estimated confidence, and look at where it is confidently wrong.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import MINUTES, MODEL_PIN_A, POLICY_DIGEST, outcome, world
from lab_common import digest
from truss.calibration import apply_map, auroc, calibration_map, ece, simulate_routing

T_AUTO, T_REFUSE = 0.956, 0.85
W = world()
fit, jan = W["fit"], W["jan"]
OUT = {}

print("Try It 1: one set of scores, five ECE protocols (January)")
OUT["ece_protocols"] = {}
_F = [c for c in fit if c["logprob"] is not None]
_m = calibration_map([c["logprob"] for c in _F], [c["correct"] for c in _F], MODEL_PIN_A, POLICY_DIGEST,
                     digest([c["logprob"] for c in _F]), "logprob")
for c in jan:
    c["calibrated"] = apply_map(_m, c["logprob"]) if c["logprob"] is not None else None
for field in ("logprob", "judge", "calibrated"):
    J = [c for c in jan if c[field] is not None]
    x = [c[field] for c in J]; y = [c["correct"] for c in J]
    for bins, strat in ((5, "uniform"), (10, "uniform"), (20, "uniform"), (10, "quantile"), (20, "quantile")):
        v = ece(x, y, bins, strat)
        OUT["ece_protocols"][f"{field}:{bins}-{strat}"] = v
        print(f"  {field:8s} {bins:2d} {strat:8s} bins: ECE {v:.4f}")
J = [c for c in jan if c["logprob"] is not None]
top = [c for c in J if c["logprob"] > 0.99]
print(f"  cases with raw score above 0.99: {len(top)}/{len(J)}, right {sum(c['correct'] for c in top)} "
      f"= {100*sum(c['correct'] for c in top)/len(top):.1f}%")
OUT["top"] = [len(top), sum(c["correct"] for c in top), len(J)]


def routed(field, label):
    F = [c for c in fit if c[field] is not None]
    m = calibration_map([c[field] for c in F], [c["correct"] for c in F], MODEL_PIN_A, POLICY_DIGEST,
                        digest([c[field] for c in F]), field)
    for c in jan:
        c["score"] = apply_map(m, c[field]) if c[field] is not None else None
    r = simulate_routing(jan, T_AUTO, T_REFUSE, outcome, MINUTES)
    distinct = sorted({round(c["score"], 4) for c in jan if c["score"] is not None})
    print(f"  {label}: map {m['digest']} a={m['params'][0]:.3f} b={m['params'][1]:.3f}; distinct calibrated values {len(distinct)}"
          f"{' ' + str(distinct) if len(distinct) < 6 else ''}")
    print(f"    auto {100*r['share']['auto']:.1f}% review {100*r['share']['review']:.1f}% refuse {100*r['share']['refuse']:.1f}% "
          f"post-review {r['post_review_wrong']}/{r['n']} = {100*r['post_review_error']:.2f}% wrong by route {r['wrong']} "
          f"officer minutes {r['officer_minutes']:.0f}")
    return m, r, distinct


print("\nTry It 2: route on the verbalised confidence (same thresholds, Platt map fitted on the same fit set)")
m2, r2, d2 = routed("verbal", "verbalised")
OUT["verbal"] = {"map": m2, "route": r2, "distinct": d2}

print("\nTry It 3: route on the judge-estimated confidence (one extra judge call per decision)")
m3, r3, d3 = routed("judge", "judge-estimated")
A = [c for c in jan if c["score"] is not None and c["score"] >= T_AUTO and not c["flags"] and not c["correct"]]
print(f"    wrong decisions the judge sent to auto: {len(A)}; segments {[c['segments'] for c in A]}")
OUT["judge"] = {"map": m3, "route": r3, "auto_wrong_segments": [c["segments"] for c in A]}
calls = len(jan)
print(f"    judge calls for these {calls} decisions at the Chapter 16 small-model price ($0.00143 a call): ${calls*0.00143:.2f}")
(HERE / "out").mkdir(exist_ok=True)
json.dump(OUT, open(HERE / "out" / "try_its.json", "w"), indent=1, default=str)
