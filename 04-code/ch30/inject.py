"""Failure injection: gateway default upgrades model mid-run."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.gateway import midrun_upgrade_detect

OUT = Path(__file__).parent / "out"

def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    clean = [fix["baseline_model"]] * 300
    dirty = fix["midrun_models"]
    out = {
        "lesson": "A gateway default that upgrades the model mid-run invalidates the paired migration table.",
        "clean": midrun_upgrade_detect(clean),
        "injected": midrun_upgrade_detect(dirty),
        "named": "midrun-gateway-default",
        "simulated": True,
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(out)

if __name__ == "__main__":
    main()
