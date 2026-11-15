"""Inject: provider deprecation that changes system+judge; expect HOLD_DUAL_PIN."""
from __future__ import annotations
import json
from pathlib import Path
from lab import pin_diff_gate

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    dep = fix["events"]["provider_deprecation_m11"]
    # healthy path: only system changes
    single = pin_diff_gate("sys-m3", "sys-m4", "judge-v3", "judge-v3")
    # failure injection: both change
    dual = pin_diff_gate(
        dep["system_pin_before"], dep["system_pin_after"],
        dep["judge_pin_before"], dep["judge_pin_after"],
    )
    assert single["verdict"] == "HOLD_SINGLE_PIN"
    assert dual["verdict"] == "HOLD_DUAL_PIN" and dual["dual_change"] is True
    out = {"single": single, "dual": dual, "SIMULATED": True}
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"single": single["verdict"], "dual": dual["verdict"]}, indent=2))


if __name__ == "__main__":
    main()
