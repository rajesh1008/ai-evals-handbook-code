"""Variance, repeats and the noise floor (Chapter 32).

Estimate run-to-run score floors, decide whether a delta is noise or a
regression once a published floor and margin exist, and compare pass@k
with pass^k on the same trials. Companion to stats (Ch31) and trajectory
pass helpers (Ch24).
"""
from __future__ import annotations

import math
import statistics
from typing import Any, Mapping, Sequence


def score_series(runs: Sequence[float]) -> dict[str, Any]:
    """Summarise repeated suite scores (percentage points on 0–100)."""
    if len(runs) < 2:
        raise ValueError("need at least two runs")
    xs = [float(x) for x in runs]
    mean = sum(xs) / len(xs)
    sd = statistics.stdev(xs)
    half_range = (max(xs) - min(xs)) / 2.0
    # Published floor uses max(sd, half_range) rounded to 1 decimal — Harbor rule.
    floor = round(max(sd, half_range), 1)
    return {
        "n_runs": len(xs),
        "scores": xs,
        "mean": mean,
        "sd": sd,
        "min": min(xs),
        "max": max(xs),
        "half_range": half_range,
        "noise_floor_pts": floor,
    }


def estimate_noise_floor(run_scores: Sequence[float], *, decimals: int = 1) -> float:
    return round(score_series(run_scores)["noise_floor_pts"], decimals)


def gate_margin_threshold(noise_floor_pts: float, margin_pts: float) -> float:
    """Absolute delta that must be exceeded to call a regression/improvement."""
    if noise_floor_pts < 0 or margin_pts < 0:
        raise ValueError("floor/margin must be non-negative")
    return float(noise_floor_pts) + float(margin_pts)


def diagnose_delta(
    delta_pts: float,
    *,
    noise_floor_pts: float,
    margin_pts: float = 0.5,
) -> dict[str, Any]:
    """Classify an observed score change against the published floor.

    Positive delta = candidate better. A drop inside the floor+margin is
    NOISE (not a regression call). Outside it is REGRESSION or IMPROVEMENT.
    """
    thr = gate_margin_threshold(noise_floor_pts, margin_pts)
    mag = abs(float(delta_pts))
    if mag <= thr:
        label = "NOISE"
    elif delta_pts < 0:
        label = "REGRESSION"
    else:
        label = "IMPROVEMENT"
    return {
        "delta_pts": float(delta_pts),
        "noise_floor_pts": float(noise_floor_pts),
        "margin_pts": float(margin_pts),
        "threshold_pts": thr,
        "label": label,
        "call_regression": label == "REGRESSION",
    }


def repeat_run_table(runs: Sequence[Mapping[str, float]]) -> dict[str, Any]:
    """Table of per-metric means/sd/floor across repeat suite runs.

    Each run is a mapping metric -> score in percentage points.
    """
    if not runs:
        raise ValueError("empty runs")
    metrics = sorted(runs[0].keys())
    rows = []
    for m in metrics:
        xs = [float(r[m]) for r in runs]
        s = score_series(xs)
        rows.append({"metric": m, **{k: s[k] for k in ("n_runs", "mean", "sd", "min", "max", "noise_floor_pts")}})
    return {"metrics": rows, "n_runs": len(runs)}


def pass_at_k_rate(trials: Sequence[bool]) -> float:
    """Share of trials that succeeded (pass@1 style on the trial list)."""
    if not trials:
        return 0.0
    return sum(1 for t in trials if t) / len(trials)


def pass_hat_k(trials: Sequence[bool]) -> float:
    """pass^k: 1 only if every trial succeeded."""
    if not trials:
        return 0.0
    return 1.0 if all(trials) else 0.0


def pass_metric_contrast(task_trials: Sequence[Sequence[bool]]) -> dict[str, Any]:
    """Contrast mean pass@k (any-success rate per task trials) vs pass^k."""
    if not task_trials:
        return {"n_tasks": 0, "pass_at_k": 0.0, "pass_hat_k": 0.0}
    at = [pass_at_k_rate(t) for t in task_trials]
    hk = [pass_hat_k(t) for t in task_trials]
    return {
        "n_tasks": len(task_trials),
        "k": len(task_trials[0]),
        "pass_at_k": sum(at) / len(at),
        "pass_hat_k": sum(hk) / len(hk),
        "n_pass_hat_k": int(sum(hk)),
    }


def sources_of_nondeterminism() -> list[str]:
    return [
        "sampling_temperature",
        "unset_or_ignored_seed",
        "batching_and_floating_point",
        "provider_silent_updates",
        "prompt_surface_and_hidden_context",
        "tool_and_retrieval_race",
        "judge_flip_on_repeats",
        "retry_context_contamination",
    ]
