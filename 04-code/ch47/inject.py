"""Failure injection: incident whose trace was never sampled must be caught."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def main():
    lab = json.loads((OUT / "lab.json").read_text())
    cov = lab["evidence_pack"]["coverage"]
    assert cov["n_missed"] >= 1
    missed = [c for c in cov["cards"] if not c["in_weekly_sample"]]
    assert any(c["linked_trace_id"] == "t-199847" for c in missed)
    assert lab["evidence_pack"]["ritual"]["ship_verb"] == "HOLD"
    out = {
        "caught": True,
        "failure": "incident_trace_never_sampled",
        "missed_trace_id": "t-199847",
        "force_include_required": True,
        "ship_blocked": True,
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(out)


if __name__ == "__main__":
    main()
