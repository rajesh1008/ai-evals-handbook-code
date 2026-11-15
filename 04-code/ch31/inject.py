"""Failure injection: unpaired comparison reports a gain the paired test erases."""
from __future__ import annotations
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.stats import paired_bootstrap_diff, unpaired_rate_diff

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
base = [p["baseline_pass"] for p in FIX["paired"]]
cand = [p["candidate_pass"] for p in FIX["paired"]]
paired = paired_bootstrap_diff(base, cand, seed=2031)
# Build an unpaired split that maximises apparent gain (SIMULATED cherry-pick)
rng = random.Random(7)
best = None
for _ in range(50):
    pool = list(enumerate(base + cand))
    rng.shuffle(pool)
    # take 200 "old" from lower-performing half of shuffled labels - crude
    labels = [x[1] for x in pool]
    g1, g2 = labels[:400], labels[400:]
    u = unpaired_rate_diff(g1, g2)
    if best is None or u["diff"] > best["diff"]:
        best = u
out = {
    "kind": "SIMULATED_INJECTION",
    "name": "unpaired_gain_erased_by_paired",
    "unpaired_best_diff": best["diff"],
    "unpaired_best": best,
    "paired_diff": paired["point_diff"],
    "paired_lo": paired["lo"],
    "paired_hi": paired["hi"],
    "paired_includes_zero": paired["includes_zero"],
    "erased": paired["includes_zero"] and abs(best["diff"]) > abs(paired["point_diff"]),
}
(OUT / "inject.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
assert out["paired_includes_zero"], "paired should include zero"
assert out["erased"] or abs(best["diff"]) >= 0.01
print("injection OK")
