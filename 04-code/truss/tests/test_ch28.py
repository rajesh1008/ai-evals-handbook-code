from truss.reviewer import (
    override_rate, approval_time_summary, agreement_with_gold, per_reviewer_table,
    automation_bias_rate, fatigue_curve, post_review_error_rate, second_review_sample,
)
from truss import __version__

def test_version():
    assert int(__version__.split(".")[1]) >= 31

def test_override_and_time():
    rows = [{"overrode": False}, {"overrode": True}, {"overrode": False}]
    assert override_rate(rows)["override_rate"] == 1/3
    s = approval_time_summary([10, 20, 30, 40, 50])
    assert s["median"] == 30

def test_agreement_and_table():
    rows = [
        {"reviewer_id": "A", "human_label": 1, "gold": 1, "overrode": False, "approval_seconds": 12},
        {"reviewer_id": "A", "human_label": 0, "gold": 1, "overrode": True, "approval_seconds": 8},
        {"reviewer_id": "B", "human_label": 1, "gold": 1, "overrode": False, "approval_seconds": 40},
    ]
    assert agreement_with_gold(rows)["n_agree"] == 2
    tab = per_reviewer_table(rows)
    assert {r["reviewer_id"] for r in tab} == {"A", "B"}

def test_bias_fatigue_post():
    rows = [
        {"ai_wrong": True, "saw_ai": True, "ai_label": 1, "human_label": 1, "gold": 0, "final_label": 1, "queue_position": 1},
        {"ai_wrong": True, "saw_ai": True, "ai_label": 1, "human_label": 0, "gold": 0, "final_label": 0, "queue_position": 2},
    ]
    assert automation_bias_rate(rows)["n_biased"] == 1
    assert len(fatigue_curve(rows, bins=2)) == 2
    assert post_review_error_rate(rows)["n_error"] == 1

def test_second_sample():
    rows = [{"i": i} for i in range(10)]
    assert len(second_review_sample(rows, 3, seed=2026)) == 3
