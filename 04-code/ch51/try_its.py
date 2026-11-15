"""Try-it helpers for Ch51 — SIMULATED."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def force_include_plan(missing_class: str) -> dict:
    return {
        "missing_class": missing_class,
        "action": "FORCE_INCLUDE_CYCLE_DAY_TRACES",
        "refuse_ship_until": ["card_for_missing_class", "billing_sme_signoff"],
        "SIMULATED": True,
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    plan = force_include_plan(fix["cases"]["toronto"]["taxonomy_missing_class"])
    (OUT / "try_its.json").write_text(json.dumps(plan, indent=2) + "\n")
    print("try_its", plan["action"])


if __name__ == "__main__":
    main()
