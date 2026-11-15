"""Three try-its for Ch32."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.noise import score_series, diagnose_delta, pass_metric_contrast, estimate_noise_floor

OUT = Path(__file__).parent / "out"

def main():
    lab = json.loads((OUT / "lab.json").read_text())
    # 1) Recompute floor from hardship scores
    h = lab["hardship"]["scores"]
    floor = estimate_noise_floor(h)
    # 2) Diagnose a 1.0 pt drop
    d1 = diagnose_delta(-1.0, noise_floor_pts=lab["published_noise_floor_pts"], margin_pts=lab["margin_pts"])
    # 3) pass contrast already in lab — tighten k by dropping last trial
    fix = json.loads((OUT / "fixture.json").read_text())
    tasks2 = [t["trials"][:2] for t in fix["task_trials"]]
    pk2 = pass_metric_contrast(tasks2)
    out = {
        "try1_recomputed_floor": floor,
        "try2_diagnose_1pt_drop": d1,
        "try3_pass_contrast_k2": pk2,
        "simulated": True,
    }
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
