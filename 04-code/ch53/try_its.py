"""Try-it variations for Ch53 (deterministic SIMULATED)."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def variation_hide_trajectory():
    """If you score only outcomes, T17 disappears — the chapter's warning."""
    fix = json.loads((OUT / "fixture.json").read_text())
    only_outcome = [c["case_id"] for c in fix["cases"] if not c["gold_outcome_ok"]]
    return {"outcome_only_fails": only_outcome, "misses_T17": "T17" not in only_outcome}


def variation_require_both_gates():
    fix = json.loads((OUT / "fixture.json").read_text())
    both = [
        c["case_id"]
        for c in fix["cases"]
        if (not c["gold_outcome_ok"]) or (not c["trajectory_ok"])
    ]
    return {"union_fails": both, "includes_T17": "T17" in both}


def variation_pending_live():
    return {"live_provider_comparison": "PENDING", "run": "do not invent live provider scores"}


if __name__ == "__main__":
    print(variation_hide_trajectory())
    print(variation_require_both_gates())
    print(variation_pending_live())
