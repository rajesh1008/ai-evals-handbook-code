"""Try-it exercises for Chapter 29."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.change import paired_case_delta, rot_staleness_scan, ownership_register

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
LAB = json.loads((OUT / "lab.json").read_text())

# 1. Recompute tool regressions and confirm plant
base = [{"case_id": c["case_id"], "pass": c["baseline"]["tool_pass"]} for c in FIX["cases"]]
cand = [{"case_id": c["case_id"], "pass": c["candidate"]["tool_pass"]} for c in FIX["cases"]]
d = paired_case_delta(base, cand)
assert "t-320118" in d["regress_ids"]

# 2. Rot after forcing all to p1
broken = [{**c, "gold_matches_current": False} for c in FIX["cases"]]
rot = rot_staleness_scan(broken, current_policy_version="p3")
assert rot["n_stale"] == FIX["n"]

# 3. Ownership refuses incomplete row
try:
    ownership_register([{"artefact": "x", "owner": "y"}])
    ok = False
except ValueError:
    ok = True

out = {
    "try1_plant_in_regress": "t-320118" in d["regress_ids"],
    "try1_n_regress": d["n_regress"],
    "try2_all_stale": rot["n_stale"],
    "try3_ownership_rejects_incomplete": ok,
    "lab_decision": LAB["experiment"]["decision"],
}
(OUT / "try_its.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
