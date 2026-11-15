"""Failure injection: a 'regression' that is inside the noise floor."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.noise import diagnose_delta

OUT = Path(__file__).parent / "out"

def main():
    lab = json.loads((OUT / "lab.json").read_text())
    fix = json.loads((OUT / "fixture.json").read_text())
    floor = lab["published_noise_floor_pts"]
    margin = lab["margin_pts"]
    drop = fix["injection"]["inside_floor_drop_pts"]
    diag = diagnose_delta(-drop, noise_floor_pts=floor, margin_pts=margin)
    # Naive gate (no floor) would false-alarm
    naive_hold = drop > 0
    correct = diag["label"] == "NOISE"
    out = {
        "simulated": True,
        "injected_drop_pts": drop,
        "naive_calls_regression": naive_hold,
        "floor_aware": diag,
        "correct_call_is_noise": correct,
        "lesson": "Inside-floor drop must not trip a REGRESSION gate; publish floor+margin first.",
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
