"""Try-it: upgrade ticket refuses missing gold freeze."""
from __future__ import annotations
import json
from pathlib import Path
from lab import upgrade_ticket

OUT = Path(__file__).parent / "out"


def main():
    t = upgrade_ticket("sys-m3", "sys-m4", "judge-v3", "gold-freeze-m10")
    assert "gold_freeze" in t["refuse_if_missing"]
    assert t["shadow_hours_required"] == 72
    (OUT / "try_its.json").write_text(json.dumps(t, indent=2))
    print(json.dumps({"shadow_hours": t["shadow_hours_required"], "judge_pin": t["judge_pin"]}, indent=2))


if __name__ == "__main__":
    main()
