"""Try-it: force-include missed incident → coverage MEETS; trophy hide missed → refuse."""
from __future__ import annotations
import json
from pathlib import Path
from lab import incident_coverage, release_ritual

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    # Force-include: add missed trace into sample
    missed = fix["missed_incident_trace_id"]
    fixed_rows = list(fix["rows"]) + [{"trace_id": missed, "flow": "hardship", "week": "2027-W24", "sampled": True, "force_included": True}]
    fix2 = dict(fix)
    fix2["rows"] = fixed_rows
    cov = incident_coverage(fix2)
    ritual = release_ritual(cov)
    trophy = {
        "visible_incidents": [c for c in fix["incidents"] if c["in_weekly_sample"]],
        "hidden_missed": 1,
        "refuse": "hiding unsampled incident traces is trophy coverage",
    }
    out = {
        "after_force_include_n_missed": cov["n_missed"],
        "after_force_include_ship": ritual["ship_verb"],
        "trophy": trophy,
    }
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2))
    print(out)


if __name__ == "__main__":
    main()
