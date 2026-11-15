"""Failure injection: regression case written against symptom instead of failure mode."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.inctoeval import regression_case, symptom_vs_failure_mode, replay_on_releases

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    bad = regression_case(
        "case-symptom-bad",
        incident_id="inc-3901",
        failure_mode="FM-fee-sycophancy",
        against="symptom",
        owner="eval-lead",
    )
    diag = symptom_vs_failure_mode(bad)
    rep = replay_on_releases(bad, fix["releases"])
    # symptom test may go green while FM still present on earlier releases
    out = {
        "simulated": True,
        "injection": "SYMPTOM_TEST",
        "case": bad,
        "diagnosis": diag,
        "replay": rep,
        "caught": diag["label"] == "SYMPTOM_TEST" and not diag["usable_as_gate"],
        "lesson": "A symptom test can go green while the failure mode still ships; write against the failure mode.",
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2)[:1200])


if __name__ == "__main__":
    main()
