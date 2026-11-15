from truss.noise import (
    score_series, estimate_noise_floor, diagnose_delta, gate_margin_threshold,
    pass_metric_contrast, sources_of_nondeterminism,
)

def test_score_series_floor():
    s = score_series([87.0, 88.5, 87.2, 88.8, 87.6])
    assert s["n_runs"] == 5
    assert s["noise_floor_pts"] >= 0.5

def test_estimate_matches_series():
    xs = [90.0, 91.0, 89.5, 90.5, 90.2]
    assert estimate_noise_floor(xs) == score_series(xs)["noise_floor_pts"]

def test_diagnose_inside_noise():
    d = diagnose_delta(-0.8, noise_floor_pts=1.4, margin_pts=0.5)
    assert d["label"] == "NOISE"
    assert d["call_regression"] is False

def test_diagnose_regression():
    d = diagnose_delta(-2.5, noise_floor_pts=1.4, margin_pts=0.5)
    assert d["label"] == "REGRESSION"
    assert gate_margin_threshold(1.4, 0.5) == 1.9

def test_pass_contrast_and_sources():
    tasks = [[True, True, False], [True, True, True], [False, True, False]]
    c = pass_metric_contrast(tasks)
    assert c["n_tasks"] == 3
    assert c["pass_hat_k"] < c["pass_at_k"] or c["pass_hat_k"] <= 1
    assert len(sources_of_nondeterminism()) >= 6
