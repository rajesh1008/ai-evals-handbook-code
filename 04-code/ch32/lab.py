"""Five-run gate suite → published noise floor; pass@k vs pass^k."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.noise import (
    score_series, estimate_noise_floor, diagnose_delta, repeat_run_table,
    pass_metric_contrast, sources_of_nondeterminism, gate_margin_threshold,
)

OUT = Path(__file__).parent / "out"

def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    runs = fix["runs"]
    table = repeat_run_table([{k: r[k] for k in ("hardship_pct", "fee_pct")} for r in runs])
    h_scores = [r["hardship_pct"] for r in runs]
    f_scores = [r["fee_pct"] for r in runs]
    h = score_series(h_scores)
    f = score_series(f_scores)
    measured_floor = estimate_noise_floor(h_scores)
    published_target = fix["published_floor_target_pts"]
    # Harbor publishes 1.4 after the five-run study; measured should match.
    use_floor = published_target if abs(measured_floor - published_target) <= 0.05 else measured_floor
    margin = fix["margin_pts"]
    thr = gate_margin_threshold(use_floor, margin)
    tasks = [t["trials"] for t in fix["task_trials"]]
    pk = pass_metric_contrast(tasks)
    base = h["mean"]
    inside = diagnose_delta(-fix["injection"]["inside_floor_drop_pts"], noise_floor_pts=use_floor, margin_pts=margin)
    outside = diagnose_delta(-fix["injection"]["outside_floor_drop_pts"], noise_floor_pts=use_floor, margin_pts=margin)
    out = {
        "seed": fix["seed"],
        "digest": fix["digest"],
        "simulated": True,
        "n_cases": fix["n_cases"],
        "n_runs": fix["n_runs"],
        "hardship": h,
        "fee": f,
        "table": table,
        "measured_noise_floor_pts": measured_floor,
        "published_noise_floor_pts": use_floor,
        "margin_pts": margin,
        "gate_threshold_pts": thr,
        "pass_contrast": pk,
        "nondeterminism_sources": sources_of_nondeterminism(),
        "baseline_hardship_mean": round(base, 2),
        "inside_floor_diag": inside,
        "outside_floor_diag": outside,
        "gate_rule": f"require |delta| > floor({use_floor}) + margin({margin}) = {thr} pts to call REGRESSION",
        "study_window": fix["study_window"],
        "scoreboard_date": fix.get("scoreboard_date"),
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({
        "digest": out["digest"],
        "measured_floor": measured_floor,
        "published_floor": use_floor,
        "threshold": thr,
        "inside": inside["label"],
        "outside": outside["label"],
        "pass_at_k": pk["pass_at_k"],
        "pass_hat_k": pk["pass_hat_k"],
        "hardship_mean": out["baseline_hardship_mean"],
        "hardship_scores": h_scores,
    }, indent=2))

if __name__ == "__main__":
    main()
