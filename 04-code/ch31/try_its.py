from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.stats import n_for_upper_bound, holm_adjust, wilson_ci

OUT = Path(__file__).parent / "out"
LAB = json.loads((OUT / "lab.json").read_text())
assert n_for_upper_bound(0.005, 0) == LAB["n_zero_fail_for_0_5pct"]
assert LAB["victor_n"] == 2400
h = holm_adjust([0.01, 0.04, 0.03])
assert h[0]["p_holm"] <= 0.05
w = wilson_ci(0, 100)
out = {"n0": LAB["n_zero_fail_for_0_5pct"], "wilson_0_100_hi": w["hi"], "holm0": h[0]["p_holm"]}
(OUT / "try_its.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
