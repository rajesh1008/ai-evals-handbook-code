"""Tests for truss.calibration (Chapter 20). Seven tests, matching prior chapters."""
import math

from truss.calibration import (apply_map, auroc, brier_decomposition, calibration_map, crc_threshold,
                               degenerate, ece, feasibility_floor, fit_isotonic, map_valid_for,
                               reliability_table, route, simulate_routing)


def test_ece_on_the_interview_table():
    # Ten answers: four stated at 0.9 (three right), six at 0.6 (three right).
    conf = [0.9] * 4 + [0.6] * 6
    right = [1, 1, 1, 0] + [1, 1, 1, 0, 0, 0]
    rows = reliability_table(conf, right, bins=10)
    assert [(r["n"], round(r["acc"], 2)) for r in rows] == [(6, 0.5), (4, 0.75)]
    # 0.6 * |0.6 - 0.5| + 0.4 * |0.9 - 0.75| = 0.06 + 0.06 = 0.12
    assert abs(ece(conf, right) - 0.12) < 1e-12


def test_constant_field_has_no_resolution_and_is_degenerate():
    conf = [1.0] * 50
    right = [1] * 47 + [0] * 3
    d = brier_decomposition(conf, right)
    assert d["resolution"] == 0.0
    assert math.isnan(auroc(conf, right)) is False and auroc(conf, right) == 0.5
    reasons = degenerate(conf)
    assert any(r.startswith("mode_share") for r in reasons) and "distinct:1" in reasons
    assert degenerate([i / 100 for i in range(1, 51)]) == []
    assert degenerate([0.5, None, 0.7, 0.9, 0.2, 0.3])[0] == "missing:1/6"


def test_isotonic_is_monotone_and_pools_violators():
    knots = fit_isotonic([0.1, 0.2, 0.3, 0.4], [0, 1, 0, 1])
    ps = [p for _, p in knots]
    assert ps == sorted(ps)
    assert knots[0] == (0.1, 0.0) and knots[1] == (0.3, 0.5) and knots[-1] == (0.4, 1.0)


def test_map_is_bound_to_model_pin_and_policy():
    conf = [0.99, 0.98, 0.97, 0.9, 0.8, 0.999, 0.995, 0.6, 0.95, 0.97]
    right = [1, 1, 1, 0, 0, 1, 1, 0, 1, 1]
    m = calibration_map(conf, right, "pin-a", "pol-1", "set-x", "logprob")
    assert map_valid_for(m, "pin-a", "pol-1") == []
    assert map_valid_for(m, "pin-b", "pol-1") == ["model_pin_changed"]
    assert map_valid_for(m, "pin-a", "pol-2") == ["policy_changed"]
    assert map_valid_for(None, "pin-a", "pol-1") == ["no_map"]
    assert 0 < apply_map(m, 0.6) < apply_map(m, 0.99) < 1
    m2 = calibration_map(conf, right, "pin-b", "pol-1", "set-x", "logprob")
    assert m2["digest"] != m["digest"]


def test_crc_threshold_and_feasibility_floor():
    scores = [i / 100 for i in range(100)]
    errors = [s < 0.20 for s in scores]  # all errors sit below 0.20
    r = crc_threshold(scores, errors, alpha=0.02)
    assert r["t"] == 0.2 and r["errors"] == 0 and r["n_auto"] == 80
    assert abs(r["bound"] - 1 / 81) < 1e-12
    assert feasibility_floor(0.054, 0.01) == (0.054 - 0.01) / (1 - 0.01)
    assert feasibility_floor(0.004, 0.01) == 0.0


def test_route_fails_closed():
    assert route(0.99) == ("auto", "above_auto")
    assert route(0.90) == ("review", "between")
    assert route(0.50) == ("refuse", "below_refuse")
    assert route(None) == ("refuse", "fail_closed:missing_score")
    assert route(0.99, flags=("stated_work",)) == ("review", "flag:stated_work")
    assert route(0.99, map_reasons=("model_pin_changed",))[0] == "review"
    assert route(0.99, field_reasons=("distinct:1",))[0] == "review"


def test_simulate_routing_counts_load_and_overload():
    cases = ([{"score": 0.99, "flags": (), "correct": True}] * 6
             + [{"score": 0.99, "flags": (), "correct": False}]
             + [{"score": 0.90, "flags": (), "correct": False}] * 2
             + [{"score": None, "flags": (), "correct": True}])

    def outcome(c, r, overloaded=False):
        return (r == "auto" and not c["correct"]) or (r == "review" and not c["correct"] and overloaded)

    r = simulate_routing(cases, 0.96, 0.85, outcome)
    assert r["count"] == {"auto": 7, "review": 2, "refuse": 1}
    assert r["post_review_wrong"] == 1 and r["officer_minutes"] == 2 * 4 + 12
    r2 = simulate_routing(cases, 0.96, 0.85, outcome, capacity_minutes=10)
    assert r2["overloaded"] and r2["post_review_wrong"] == 3
