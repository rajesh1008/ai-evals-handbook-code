"""Failure injection: cheaper judge that fails the bias battery."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.costknow import bias_battery_gate

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    inj = fix["inject"]
    gate = bias_battery_gate(
        tpr=inj["cheap_tpr"],
        tnr=inj["cheap_tnr"],
        position_flip_rate=inj["position_flip_rate"],
    )
    out = {
        "injection": inj["label"],
        "simulated": True,
        "gate": gate,
        "lesson": (
            "A cheaper judge that clears TPR/TNR floors can still fail the bias battery; "
            "Harbor refuses the cost cut until flip rate falls."
        ),
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
