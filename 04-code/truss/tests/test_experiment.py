from math import comb
from truss.experiment import (
    paired_table,
    unpaired_resample_rank,
    multiple_comparison_note,
    n_pairwise_comparisons,
    n_vs_control_comparisons,
    register_experiment,
    frontier_points,
    discordant_counts,
    mcnemar_exact,
    paired_contrast,
)


def test_paired_rank_stable():
    s = {"a": [0, 0, 1, 0], "b": [1, 1, 1, 0]}
    t = paired_table(s)
    assert t["ranking"][0] == "a"
    assert t["n"] == 4


def test_unpaired_can_differ():
    a = [0] * 50 + [1] * 50
    b = [1] * 50 + [0] * 50
    paired = paired_table({"a": a, "b": b})
    un = unpaired_resample_rank({"a": a, "b": b}, seed=3, take=50)
    assert un["mode"] == "unpaired_subsample"
    assert paired["n"] == 100


def test_bonferroni_uses_comparisons_not_systems():
    # 4 systems all-pairs => 6 tests, not 4
    assert n_pairwise_comparisons(4) == 6
    assert n_vs_control_comparisons(4) == 3
    assert n_pairwise_comparisons(5) == 10
    assert n_vs_control_comparisons(5) == 4
    m6 = multiple_comparison_note(6, structure="all_pairs", n_systems=4)
    assert abs(m6["per_comparison_alpha"] - 0.05 / 6) < 1e-12
    assert m6["family_tests"] == 6
    m3 = multiple_comparison_note(3, structure="vs_control", n_systems=4)
    assert abs(m3["per_comparison_alpha"] - 0.05 / 3) < 1e-12
    # Wrong mapping regressions: must NOT equal alpha/n_systems for all-pairs
    assert abs(m6["per_comparison_alpha"] - 0.0125) > 1e-9  # not alpha/4
    m10 = multiple_comparison_note(10, structure="all_pairs", n_systems=5)
    assert abs(m10["per_comparison_alpha"] - 0.05 / 10) < 1e-12
    assert abs(m10["per_comparison_alpha"] - 0.01) > 1e-9  # not alpha/5
    # Discarded hypotheses still enlarge the family
    m_disc = multiple_comparison_note(6, discarded_hypotheses=2, structure="all_pairs", n_systems=4)
    assert m_disc["family_tests"] == 8
    assert abs(m_disc["per_comparison_alpha"] - 0.05 / 8) < 1e-12
    assert m6["controls"] == "family_wise_error_rate"


def test_mcnemar_exact_and_contrast():
    # Classic: n10=0, n01=2 => p = 2*(1+2)/4 = 1.5? Wait 2^2=4; C(2,0)+C(2,1)=1+2=3; 2*3/4=1.5 -> min 1.0
    # Actually min(n10,n01)=0; sum k=0..0 C(2,0)=1; 2*1/4=0.5
    m = mcnemar_exact(0, 2)
    assert abs(m["p_value_exact"] - 0.5) < 1e-12
    m2 = mcnemar_exact(0, 6)
    # 2 * 1 / 2^6 = 2/64 = 0.03125
    assert abs(m2["p_value_exact"] - 0.03125) < 1e-12
    a = [1, 1, 0, 0, 0, 0]
    b = [1, 0, 1, 0, 0, 0]
    d = discordant_counts(a, b)
    assert d["n11"] == 1 and d["n10"] == 1 and d["n01"] == 1 and d["n00"] == 3
    pc = paired_contrast(a, b, name_a="a", name_b="b")
    assert pc["table"]["discordant"] == 2
    assert "wilson_intervals_overlap" in pc


def test_register_and_frontier():
    rec = register_experiment(
        experiment_id="t", systems=["a", "b"], n_paired=10, digest="abc", hypothesis="h", owner="o"
    )
    assert len(rec["record_sha12"]) == 12
    pts = frontier_points(
        [
            {"system": "cheap", "error_rate": 0.02, "cost_usd_per_1k": 0.3},
            {"system": "mid", "error_rate": 0.01, "cost_usd_per_1k": 0.9},
            {"system": "dominated", "error_rate": 0.03, "cost_usd_per_1k": 1.0},
        ]
    )
    assert any(p["system"] == "cheap" and p["on_frontier"] for p in pts)
