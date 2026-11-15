"""Chapter 20 failure injection: a constant confidence field that passes every schema check.

A serialiser change writes the schema default, 1.0, into the decision
confidence on every trace (SIMULATED, replayed over the four live weeks of
17 January to 13 February 2028). The
field is a float between 0 and 1 on every trace, so the trace contract's
type and range checks pass. Routing on it, then routing with the degenerate
check in front of it.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import MINUTES, MODEL_PIN_A, POLICY_DIGEST, outcome, world
from truss.calibration import (apply_map, auroc, brier_decomposition, calibration_map, degenerate,
                               ece, simulate_routing)

T_AUTO, T_REFUSE = 0.956, 0.85
W = world()
F = [c for c in W["fit"] if c["logprob"] is not None]
from lab_common import digest
cmap = calibration_map([c["logprob"] for c in F], [c["correct"] for c in F], MODEL_PIN_A, POLICY_DIGEST,
                       digest([c["logprob"] for c in F]), "logprob")
week = copy.deepcopy([c for wk in W["live"].values() for c in wk])
bad = copy.deepcopy(week)
for c in bad:
    c["logprob"] = 1.0


def schema_ok(c):
    v = c["logprob"]
    return isinstance(v, float) and 0.0 <= v <= 1.0  # what the trace contract checks


for c in week + bad:
    c["score"] = apply_map(cmap, c["logprob"]) if c["logprob"] is not None else None

print("Schema check (float in [0, 1]) on the injected week:",
      f"{sum(schema_ok(c) for c in bad)}/{len(bad)} pass")
print(f"Calibrated score of 1.0 under map {cmap['digest']}: {apply_map(cmap, 1.0):.4f} (t_auto {T_AUTO})")
y = [c["correct"] for c in bad]
x = [c["logprob"] for c in bad]
d = brier_decomposition(x, y)
print(f"Injected field: ECE {ece(x, y):.4f}, AUROC {auroc(x, y):.3f}, resolution {d['resolution']:.4f}, "
      f"degenerate {degenerate(x)}")
honest = simulate_routing(week, T_AUTO, T_REFUSE, outcome, MINUTES)
blind = simulate_routing(bad, T_AUTO, T_REFUSE, outcome, MINUTES)
guarded = simulate_routing(bad, T_AUTO, T_REFUSE, outcome, MINUTES, field_reasons=degenerate(x))
res = {}
for name, r in (("honest field", honest), ("constant, no guard", blind), ("constant, degenerate guard", guarded)):
    res[name] = r
    print(f"  {name:28s} auto {100*r['share']['auto']:5.1f}% review {100*r['share']['review']:5.1f}% "
          f"refuse {100*r['share']['refuse']:4.1f}% post-review {r['post_review_wrong']}/{r['n']} = "
          f"{100*r['post_review_error']:.2f}% wrong by route {r['wrong']} officer minutes {r['officer_minutes']:.0f}")
print("The guard keeps every decision in front of an officer; the routing share itself",
      "(auto jumping from about 61% to the share of unflagged cases) is the label-free alarm.")
(HERE / "out").mkdir(exist_ok=True)
json.dump({k: v for k, v in res.items()}, open(HERE / "out" / "inject.json", "w"), indent=1, default=str)
