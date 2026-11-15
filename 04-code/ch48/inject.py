"""Failure injection: vocabulary-reward rubric inverts hiring rank."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def main():
    lab = json.loads((OUT / "lab.json").read_text())
    ep = lab["evidence_pack"]
    assert ep["inversion"] is True
    assert ep["winner_findings"] == "A"
    assert ep["winner_vocabulary"] == "B"
    # Confirm B has higher vocab score and lower findings score
    by = {r["candidate"]: r for r in ep["rows"]}
    assert by["B"]["vocabulary"]["score"] > by["A"]["vocabulary"]["score"]
    assert by["A"]["findings"]["score"] > by["B"]["findings"]["score"]
    out = {
        "caught": True,
        "failure": "rubric_rewards_vocabulary_over_findings",
        "winner_under_bad_rubric": "B",
        "winner_under_findings_rubric": "A",
        "inversion": True,
        "SIMULATED": True,
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(out)


if __name__ == "__main__":
    main()
