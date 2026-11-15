"""Three Try Its — offline. Multiplicity counts TESTS, not systems."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.experiment import (
    paired_table,
    multiple_comparison_note,
    n_pairwise_comparisons,
    n_vs_control_comparisons,
)

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    systems = fix["systems_binary_fail"]
    # 1: drop worst prompt from the *displayed* table — family of searched tests does NOT shrink
    subset = {k: systems[k] for k in ["prompt_v1", "prompt_v2", "small_fee_model"]}
    t1 = paired_table(subset)
    # Original declared family was all-pairs among 4 → 6; discarding v3 after peeking must still
    # count the searched comparisons (do not auto-reduce to C(3,2)=3).
    mc_honest = multiple_comparison_note(
        n_pairwise_comparisons(4),
        structure="all_pairs",
        n_systems=4,
        discarded_hypotheses=0,  # v3 pairwise tests were in the search; keep family_tests=6
    )
    # 2: five systems — all-pairs=10 or vs_control=4 (never alpha/5)
    t2_pairs = multiple_comparison_note(
        n_pairwise_comparisons(5), structure="all_pairs", n_systems=5
    )
    t2_ctrl = multiple_comparison_note(
        n_vs_control_comparisons(5), structure="vs_control", n_systems=5
    )
    # 3: only prompts (no SLM) ranked — still report original search family if SLM was searched
    prompts = {k: systems[k] for k in ["prompt_v1", "prompt_v2", "prompt_v3"]}
    t3 = paired_table(prompts)
    out = [
        {
            "name": "drop_worst_prompt_display",
            "ranking": t1["ranking"],
            "note": "display may omit v3; declared all-pairs family among 4 remains 6 tests",
            "family_tests_if_honest": mc_honest["family_tests"],
            "per_comparison_alpha_honest": mc_honest["per_comparison_alpha"],
            "wrong_if_shrink_to_three_systems_all_pairs": 0.05 / 3,
        },
        {
            "name": "five_systems_multiplicity",
            "all_pairs_n": n_pairwise_comparisons(5),
            "all_pairs_alpha": t2_pairs["per_comparison_alpha"],
            "vs_control_n": n_vs_control_comparisons(5),
            "vs_control_alpha": t2_ctrl["per_comparison_alpha"],
            "wrong_alpha_if_divide_by_five_systems": 0.01,
        },
        {"name": "prompts_only", "ranking": t3["ranking"]},
    ]
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
