"""Assert failure injection: lint-clean config with unvalidated judge is HOLD."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def main():
    lab = json.loads((OUT / "lab.json").read_text())
    ep = lab["evidence_pack"]
    caught = bool(ep["inject_caught"])
    payload = {
        "caught": caught,
        "failure": "config_lints_clean_but_unvalidated_judge_gates_release",
        "inject_config": ep["inject_config"],
        "lint_pass": ep["inject_lint_pass"],
        "gate": ep["inject_gate"],
        "reason": ep["inject_reason"],
        "SIMULATED": True,
    }
    (OUT / "inject.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
