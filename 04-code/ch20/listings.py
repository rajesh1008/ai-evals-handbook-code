"""The short listings printed in Chapter 20, run against the same SIMULATED world.

Each block below is the code shown in the chapter (after the setup lines) and
its output is what the chapter prints under it.
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "truss"))
from fixture import MODEL_PIN_A, MODEL_PIN_B, POLICY_DIGEST, world
from lab_common import digest
from truss.calibration import (auroc, brier_decomposition, calibration_map, degenerate, ece,
                               map_valid_for, reliability_table, route)

W = world()
fit, jan = W["fit"], W["jan"]
F = [c for c in fit if c["logprob"] is not None]
J = [c for c in jan if c["logprob"] is not None]

print("--- Listing 20.1")
conf = [c["logprob"] for c in J]; ok = [c["correct"] for c in J]
for r in reliability_table(conf, ok, bins=10):
    print(f"({r['lo']:.1f},{r['hi']:.1f}] n={r['n']:3d} conf={r['conf']:.3f} acc={r['acc']:.3f}")
print(f"ECE {ece(conf, ok):.4f}  AUROC {auroc(conf, ok):.3f}")
d = brier_decomposition(conf, ok)
print(f"reliability {d['reliability']:.4f} resolution {d['resolution']:.4f} uncertainty {d['uncertainty']:.4f}")

print("--- Listing 20.4")
x = [c["logprob"] for c in F]; y = [c["correct"] for c in F]
cmap = calibration_map(x, y, MODEL_PIN_A, POLICY_DIGEST, digest(x), "logprob")
print(cmap["digest"], cmap["kind"], cmap["n"])
print(map_valid_for(cmap, MODEL_PIN_A, POLICY_DIGEST))
print(map_valid_for(cmap, MODEL_PIN_B, POLICY_DIGEST))

print("--- Listing 20.2")
kw = dict(t_auto=0.956, t_refuse=0.85)
print(route(0.97, **kw))
print(route(0.91, **kw))
print(route(0.97, flags=("stated_work",), **kw))
print(route(None, **kw))
print(route(0.97, map_reasons=("model_pin_changed",), **kw))

print("--- Listing 20.3")
print(degenerate([c["verbal"] for c in fit]))
print(degenerate([1.0] * 560))
print(degenerate(conf))

print("--- Threshold sweep on unflagged auto-route decisions (fit map; fit set is in-sample)")
from truss.calibration import apply_map
from truss.rates import upper_bound
for S, name in ((fit, "fit"), (jan, "jan")):
    for t in (0.90, 0.93, 0.956, 0.97, 0.98, 0.99):
        A = [c for c in S if c["logprob"] is not None and not c["flags"] and apply_map(cmap, c["logprob"]) >= t]
        k = sum(not c["correct"] for c in A)
        print(f"{name} t={t:.3f} auto={len(A):3d} wrong={k} exact95={100 * upper_bound(k, len(A)):.2f}%")

print("--- Below the refuse threshold (calibrated < 0.85)")
for S, name in ((F, "fit"), (J, "jan")):
    L = [c for c in S if apply_map(cmap, c["logprob"]) < 0.85]
    print(f"{name}: {len(L)} decisions, {sum(c['correct'] for c in L)} right")

print("--- Decisions with no recorded action-token probability")
M = [c for c in jan if c["logprob"] is None]
print(f"jan: {len(M)} missing, {sum(c['correct'] for c in M)} right as drafted")
M = [c for wk in W["live"].values() for c in wk if c["logprob"] is None]
print(f"live: {len(M)} missing, {sum(c['correct'] for c in M)} right as drafted")

print("--- Second-read decisions needed for an exact 95% bound under 1% at the live error rate")
for k in (4, 6, 8):
    n = next(n for n in range(100, 5000) if upper_bound(k, n) < 0.01)
    print(f"{k} wrong: {n} decisions")
print(f"launch second reads: 560 x $13.90 = ${560 * 13.90:,.0f}; steady state 60 a week = ${60 * 13.90:,.0f}")

print("--- Missing scores by live week")
for wk, L in W["live"].items():
    print(wk, sum(c["logprob"] is None for c in L))

print("--- Threshold sweep on the recalibration draw under the new map (in-sample)")
R = [c for c in W["recal"] if c["logprob"] is not None]
xb = [c["logprob"] for c in R]; yb = [c["correct"] for c in R]
cmap_b = calibration_map(xb, yb, MODEL_PIN_B, POLICY_DIGEST, digest(xb), "logprob")
print(cmap_b["digest"])
for t in (0.93, 0.956, 0.99):
    A = [c for c in R if not c["flags"] and apply_map(cmap_b, c["logprob"]) >= t]
    k = sum(not c["correct"] for c in A)
    print(f"recal t={t:.3f} auto={len(A):3d} wrong={k} exact95={100 * upper_bound(k, len(A)):.2f}%")
