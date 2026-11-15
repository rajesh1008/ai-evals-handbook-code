"""Three Try-it variations on the config linter."""
from __future__ import annotations
import json, copy
from pathlib import Path
from lab import lint_config, release_gate

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    bad = copy.deepcopy(fix["configs"]["linter_pass_unvalidated_judge"])
    # 1) Validate the judge → gate should PASS
    fixed = copy.deepcopy(bad)
    fixed["judge"]["validated"] = True
    fixed["judge"]["gold_n"] = 100
    fixed["judge"]["agreement_beyond_chance"] = True
    fixed["judge"]["bias_probe"] = True
    del fixed["FAILURE_INJECTION"]
    lint1 = lint_config(fixed)
    gate1 = release_gate(fixed, lint1)
    # 2) Drop suite digest → lint fails before gate
    broken = copy.deepcopy(bad)
    broken["suite_digest"] = "ab"
    lint2 = lint_config(broken)
    gate2 = release_gate(broken, lint2)
    # 3) Monitor-only gate that still requires validated judge
    mon = copy.deepcopy(bad)
    mon["gate"]["kind"] = "monitor"
    lint3 = lint_config(mon)
    gate3 = release_gate(mon, lint3)
    payload = {
        "validate_judge_then_pass": {"lint_pass": lint1["lint_pass"], "gate": gate1["gate_result"]},
        "short_digest_lint_hold": {"lint_pass": lint2["lint_pass"], "gate": gate2["gate_result"], "errors": lint2["errors"]},
        "monitor_still_holds_unvalidated": {"lint_pass": lint3["lint_pass"], "gate": gate3["gate_result"], "reason": gate3["reason"]},
        "SIMULATED": True,
    }
    (OUT / "try_its.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
