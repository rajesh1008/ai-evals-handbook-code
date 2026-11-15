"""Chapter 42 lab: paired comparative eval + experiment registry. Offline SIM."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.experiment import (
    paired_table,
    unpaired_resample_rank,
    multiple_comparison_note,
    n_pairwise_comparisons,
    n_vs_control_comparisons,
    router_component_card,
    register_experiment,
    frontier_points,
    paired_contrast,
)

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    systems = fix["systems_binary_fail"]
    names = list(systems)
    paired = paired_table(systems)
    unpaired = unpaired_resample_rank(systems, seed=fix["seed"], take=250)
    assert paired["ranking"] != unpaired["ranking"], (paired["ranking"], unpaired["ranking"])

    # Declared family: all pairwise contrasts among 4 registered systems → C(4,2)=6
    n_systems = len(names)
    n_all_pairs = n_pairwise_comparisons(n_systems)
    n_control = n_vs_control_comparisons(n_systems)
    mc = multiple_comparison_note(
        n_all_pairs,
        alpha=0.05,
        structure="all_pairs",
        n_systems=n_systems,
        discarded_hypotheses=0,
    )
    mc_vs_control = multiple_comparison_note(
        n_control,
        alpha=0.05,
        structure="vs_control",
        n_systems=n_systems,
    )
    # Wrong mappings kept as regression witnesses (must not be used as the teaching alpha)
    wrong_as_systems = {"n_systems": n_systems, "incorrect_alpha_if_divide_by_systems": 0.05 / n_systems}
    wrong_five_as_systems = {"n_systems": 5, "incorrect_alpha_if_divide_by_systems": 0.05 / 5,
                             "correct_all_pairs": 0.05 / n_pairwise_comparisons(5),
                             "correct_vs_control": 0.05 / n_vs_control_comparisons(5)}

    declared_comparisons = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            declared_comparisons.append({"a": a, "b": b, "kind": "pairwise_error_rate"})

    # Worked paired contrast: prompt_v2 vs small_fee_model on the same matrix
    contrast_v2_slm = paired_contrast(
        systems["prompt_v2"],
        systems["small_fee_model"],
        name_a="prompt_v2",
        name_b="small_fee_model",
    )
    # Also v2 vs v1 for a significant teaching contrast
    contrast_v2_v1 = paired_contrast(
        systems["prompt_v2"],
        systems["prompt_v1"],
        name_a="prompt_v2",
        name_b="prompt_v1",
    )

    router = router_component_card(
        route_accuracy=fix["router_sim"]["route_accuracy"],
        oracle_accuracy=fix["router_sim"]["oracle_accuracy"],
        cost_per_query_usd=fix["router_sim"]["cost_per_query_usd"],
        n=fix["router_sim"]["n"],
        owner="Ryan",
    )
    cost = fix["costs_usd_per_1k"]
    for row in paired["rows"]:
        row["cost_usd_per_1k"] = cost[row["system"]]
    frontier = frontier_points(paired["rows"])
    rec = register_experiment(
        experiment_id="harbor-fee-compare-2029-06",
        systems=list(systems),
        n_paired=fix["n_paired"],
        digest=fix["digest"],
        hypothesis=(
            "all_pairs among 4 fee systems (C(4,2)=6); "
            "prompt_v2 beats v1/v3 on paired error; SLM near v2 at 1/3 SIM cost; "
            "hardship stays frontier; no non-inferiority margin pre-registered"
        ),
        owner="eval-lead",
    )
    for row in paired["rows"]:
        row["meets_fee_gate"] = row["wilson_hi"] < fix["policy"]["wrong_fee_target"]

    lab = {
        "seed": fix["seed"],
        "digest": fix["digest"],
        "simulated": True,
        "label": "SIMULATED",
        "n_paired": fix["n_paired"],
        "paired": paired,
        "unpaired_injection": unpaired,
        "ranking_reversed": paired["ranking"] != unpaired["ranking"],
        "multiple_comparison": mc,
        "multiple_comparison_vs_control": mc_vs_control,
        "wrong_mapping_regressions": {
            "four_systems_divided_by_systems_not_tests": wrong_as_systems,
            "five_systems_example": wrong_five_as_systems,
        },
        "declared_comparisons": declared_comparisons,
        "paired_contrasts": {
            "prompt_v2_vs_small_fee_model": contrast_v2_slm,
            "prompt_v2_vs_prompt_v1": contrast_v2_v1,
        },
        "router": router,
        "frontier": frontier,
        "experiment_record": rec,
        "policy": fix["policy"],
        "costs_usd_per_1k": cost,
        "teaching": {
            "paired_winner": paired["ranking"][0],
            "unpaired_winner": unpaired["ranking"][0],
            "slm_cost_ratio_vs_prompt": cost["small_fee_model"] / cost["prompt_v1"],
            "hardship_on_frontier": True,
            "family_structure": "all_pairs",
            "n_comparisons": n_all_pairs,
        },
    }
    (OUT / "lab.json").write_text(json.dumps(lab, indent=2))
    print(json.dumps({
        "digest": lab["digest"],
        "paired_ranking": paired["ranking"],
        "unpaired_ranking": unpaired["ranking"],
        "reversed": lab["ranking_reversed"],
        "n_comparisons": n_all_pairs,
        "per_comparison_alpha": mc["per_comparison_alpha"],
        "v2_slm_mcnemar_p": contrast_v2_slm["mcnemar"]["p_value_exact"],
        "v2_slm_discordant": contrast_v2_slm["table"]["discordant"],
    }, indent=2))
    return lab


if __name__ == "__main__":
    main()
