from truss.stats import (
    wilson_ci, n_for_upper_bound, paired_bootstrap_diff, unpaired_rate_diff,
    holm_adjust, signature7_wall, bonferroni_alpha,
    cluster_paired_bootstrap_diff, sequential_holm_looks,
)
from truss import __version__

def test_version():
    assert int(__version__.split(".")[1]) >= 34

def test_wilson_and_n():
    w = wilson_ci(0, 100)
    assert w["hi"] < 0.05
    assert n_for_upper_bound(0.005, 0) >= 500

def test_paired_unpaired():
    b = [1,1,0,0,1,1,0,0] * 10
    c = [1,0,1,0,1,0,1,0] * 10
    p = paired_bootstrap_diff(b, c, reps=500, seed=1)
    assert "includes_zero" in p
    u = unpaired_rate_diff(b, c)
    assert "diff" in u

def test_holm_bonf_wall():
    h = holm_adjust([0.01, 0.04, 0.20])
    assert h[0]["p_holm"] <= 0.03
    assert bonferroni_alpha(0.05, 8) == 0.05/8
    wall = signature7_wall([{"claim": "x", "kind": "zero_fail_upper", "target": 0.005}])
    assert wall[0]["n_required"] >= 500

def test_lab():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "ch31" / "out" / "lab.json"
    if not p.exists():
        return
    d = json.loads(p.read_text())
    assert d["victor_n"] == 2400
    assert d["paired"]["includes_zero"]


def test_cluster_vs_row_bootstrap():
    # SIMULATED fixture: 40 clusters × 10 rows; 8 clusters wholly worse on candidate
    baseline, candidate, clusters = [], [], []
    for b_i in range(40):
        for _ in range(10):
            clusters.append(f"b{b_i}")
            if b_i < 8:
                baseline.append(1); candidate.append(0)
            else:
                baseline.append(1); candidate.append(1)
    c = cluster_paired_bootstrap_diff(baseline, candidate, clusters, reps=800, seed=2031)
    assert c["n_clusters"] == 40 and c["n"] == 400
    assert c["width_ratio_vs_naive"] is not None and c["width_ratio_vs_naive"] > 1.5
    assert c["fixture_status"] != "REAL" if "fixture_status" in c else True
    assert c["sample_unit"] == "cluster"

def test_sequential_holm_looks():
    # SIMULATED p-schedule: continue, continue, stop at look 3
    looks = [
        [0.20, 0.40, 0.50, 0.60],
        [0.04, 0.20, 0.30, 0.40],
        [0.004, 0.02, 0.10, 0.25],
    ]
    s = sequential_holm_looks(looks, alpha=0.05)
    assert s["fixture_status"] == "SIMULATED"
    assert s["stopped"] is True and s["stop_look"] == 3
    assert s["looks"][0]["decision"] == "CONTINUE"
    assert s["looks"][2]["survivors"][0]["p_holm"] == 0.016
