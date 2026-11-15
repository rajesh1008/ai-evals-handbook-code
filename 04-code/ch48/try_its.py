"""Try-it variations for Ch48 hiring lab."""
from __future__ import annotations
import json
from pathlib import Path
from lab import score_findings, score_vocabulary

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    # 1) Repair: strip vocabulary inflation — rescore B notes only on findings
    b = fix["reviews"]["vocabulary_heavy"]
    # Candidate B after coaching: keep notes but require gold labels
    coached = {
        "candidate": "B_coached",
        "notes": [
            {"trace_id": "t-48001", "finding": "offer_before_income", "evidence": "income unset"},
            {"trace_id": "t-48004", "finding": "missing_officer_handoff", "evidence": "no escalate"},
        ],
        "vocab_hits": b["vocab_hits"],
    }
    fr = score_findings(coached)
    # 2) Trophy: count how many vocab tokens appear in B without any planted hit
    planted_hits_b = score_findings(fix["reviews"]["vocabulary_heavy"])["hits"]
    trophy = {
        "vocab_tokens_without_planted_hits": len(b["vocab_hits"]) if planted_hits_b == 0 else len(b["vocab_hits"]),
        "planted_hits_b": planted_hits_b,
        "coached_s1_hits": fr["s1_hits"],
        "coached_findings_score": fr["score"],
    }
    # 3) Weight sensitivity: if S1 weight drops to 1, does A still win findings?
    # (manual: A has both S1; still wins)
    out = {
        "SIMULATED": True,
        "coached_B_findings": fr,
        "trophy": trophy,
        "try_its": [
            "replace vocabulary rubric with findings rubric before any hire decision",
            "coach candidate B to label planted S1 findings with evidence spans",
            "require at least one S1 hit before vocabulary may be scored at all",
        ],
    }
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2)[:500])


if __name__ == "__main__":
    main()
