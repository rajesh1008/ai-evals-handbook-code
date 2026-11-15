"""Statistics you can defend (Chapter 31).

Wilson and Clopper–Pearson helpers (via rates), sample-size planners,
paired bootstrap differences, unpaired (misleading) deltas, multiple-comparison
adjustments, stratified rate tables, effect sizes, and Signature 7 wall rows.
"""
from __future__ import annotations

import math
import random
from typing import Any, Mapping, Sequence

from truss.rates import wilson, upper_bound, traces_needed


def wilson_ci(k: int, n: int, z: float = 1.96) -> dict[str, Any]:
    lo, hi = wilson(k, n, z=z)
    return {"k": k, "n": n, "rate": (k / n) if n else 0.0, "lo": lo, "hi": hi, "method": "wilson"}


def clopper_upper(failures: int, n: int, confidence: float = 0.95) -> dict[str, Any]:
    return {
        "failures": failures,
        "n": n,
        "rate": (failures / n) if n else 0.0,
        "upper": upper_bound(failures, n, confidence),
        "confidence": confidence,
        "method": "clopper_pearson_one_sided",
    }


def n_for_upper_bound(target: float, failures: int = 0, confidence: float = 0.95) -> int:
    return traces_needed(target, failures=failures, confidence=confidence)


def n_for_margin(p: float, margin: float, z: float = 1.96) -> int:
    """Approximate n so Wilson/normal half-width ≈ margin at rate p."""
    if margin <= 0 or p < 0 or p > 1:
        raise ValueError("bad p/margin")
    # n ≈ z^2 p(1-p) / margin^2 , inflate slightly for Wilson
    raw = (z * z * p * (1 - p)) / (margin * margin)
    return max(1, int(math.ceil(raw * 1.1)))


def paired_bootstrap_diff(
    baseline: Sequence[int | bool],
    candidate: Sequence[int | bool],
    *,
    reps: int = 2000,
    seed: int = 2031,
) -> dict[str, Any]:
    """Bootstrap CI for mean(candidate - baseline) on paired 0/1 outcomes."""
    if len(baseline) != len(candidate) or not baseline:
        raise ValueError("paired lengths")
    b = [1 if x else 0 for x in baseline]
    c = [1 if x else 0 for x in candidate]
    n = len(b)
    deltas = [c[i] - b[i] for i in range(n)]
    point = sum(deltas) / n
    rng = random.Random(seed)
    boots = []
    for _ in range(reps):
        s = 0.0
        for _ in range(n):
            j = rng.randrange(n)
            s += deltas[j]
        boots.append(s / n)
    boots.sort()
    lo = boots[int(0.025 * reps)]
    hi = boots[int(0.975 * reps) - 1]
    return {
        "n": n,
        "point_diff": point,
        "lo": lo,
        "hi": hi,
        "includes_zero": lo <= 0.0 <= hi,
        "baseline_rate": sum(b) / n,
        "candidate_rate": sum(c) / n,
        "method": "paired_bootstrap",
        "reps": reps,
    }


def unpaired_rate_diff(
    baseline: Sequence[int | bool],
    candidate: Sequence[int | bool],
) -> dict[str, Any]:
    """Naive unpaired difference of means (can invent a gain pairing erases)."""
    b = [1 if x else 0 for x in baseline]
    c = [1 if x else 0 for x in candidate]
    if not b or not c:
        raise ValueError("empty")
    br, cr = sum(b) / len(b), sum(c) / len(c)
    return {
        "n_base": len(b),
        "n_cand": len(c),
        "baseline_rate": br,
        "candidate_rate": cr,
        "diff": cr - br,
        "method": "unpaired_mean_diff",
    }


def holm_adjust(p_values: Sequence[float]) -> list[dict[str, Any]]:
    """Holm–Bonferroni adjusted p-values (sorted report, original index kept)."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        factor = m - rank
        val = min(1.0, p_values[i] * factor)
        running = max(running, val)
        adj[i] = running
    return [{"index": i, "p": p_values[i], "p_holm": adj[i]} for i in range(m)]


def bonferroni_alpha(alpha: float, m: int) -> float:
    if m < 1:
        raise ValueError("m")
    return alpha / m


def stratified_rates(
    rows: Sequence[Mapping[str, Any]],
    *,
    slice_key: str = "slice",
    fail_key: str = "fail",
) -> list[dict[str, Any]]:
    buckets: dict[str, list[int]] = {}
    for r in rows:
        buckets.setdefault(str(r[slice_key]), []).append(1 if r[fail_key] else 0)
    out = []
    for name in sorted(buckets):
        fails = buckets[name]
        k = sum(fails)
        n = len(fails)
        ci = wilson_ci(k, n)
        out.append({"slice": name, **ci, "upper95": upper_bound(k, n, 0.95)})
    return out


def risk_diff_effect(p0: float, p1: float) -> dict[str, float]:
    """Absolute and relative risk difference (effect size for rates)."""
    rd = p1 - p0
    rr = (p1 / p0) if p0 > 0 else float("inf")
    return {"risk_diff": rd, "risk_ratio": rr, "abs_risk_diff": abs(rd)}


def signature7_wall(claims: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Rows for Signature 7: claim → n required under a stated rule."""
    out = []
    for c in claims:
        kind = c["kind"]
        if kind == "zero_fail_upper":
            n = n_for_upper_bound(c["target"], failures=0, confidence=c.get("confidence", 0.95))
        elif kind == "margin":
            n = n_for_margin(c["p"], c["margin"])
        elif kind == "fixed":
            n = int(c["n"])
        else:
            raise ValueError(kind)
        out.append({"claim": c["claim"], "kind": kind, "n_required": n, **{k: c[k] for k in c if k not in ("claim", "kind")}})
    return out


def permutation_p_paired(
    baseline: Sequence[int | bool],
    candidate: Sequence[int | bool],
    *,
    reps: int = 2000,
    seed: int = 2031,
) -> dict[str, Any]:
    """Two-sided paired permutation p for mean difference."""
    b = [1 if x else 0 for x in baseline]
    c = [1 if x else 0 for x in candidate]
    n = len(b)
    obs = sum(c[i] - b[i] for i in range(n)) / n
    rng = random.Random(seed)
    extreme = 0
    for _ in range(reps):
        s = 0.0
        for i in range(n):
            d = c[i] - b[i]
            s += d if rng.random() < 0.5 else -d
        if abs(s / n) >= abs(obs) - 1e-15:
            extreme += 1
    p = extreme / reps
    return {"n": n, "point_diff": obs, "p": p, "reps": reps, "method": "paired_permutation"}


def cluster_paired_bootstrap_diff(
    baseline: Sequence[int | bool],
    candidate: Sequence[int | bool],
    clusters: Sequence[str],
    *,
    reps: int = 2000,
    seed: int = 2031,
) -> dict[str, Any]:
    """Paired bootstrap that resamples *clusters* (e.g. borrower ids), not rows.

    Use when several traces share a sample unit. Resampling rows understates
    variance; resampling clusters respects the design. Fixture status: caller
    supplies SIMULATED or REAL labels outside this helper.
    """
    if not (len(baseline) == len(candidate) == len(clusters)) or not baseline:
        raise ValueError("paired lengths / clusters")
    b = [1 if x else 0 for x in baseline]
    c = [1 if x else 0 for x in candidate]
    n = len(b)
    # group row indices by cluster
    by: dict[str, list[int]] = {}
    for i, cl in enumerate(clusters):
        by.setdefault(str(cl), []).append(i)
    keys = sorted(by)
    n_clusters = len(keys)
    deltas = [c[i] - b[i] for i in range(n)]
    point = sum(deltas) / n
    rng = random.Random(seed)
    boots: list[float] = []
    for _ in range(reps):
        # resample clusters with replacement; take all rows in drawn clusters
        drawn_rows: list[int] = []
        for _k in range(n_clusters):
            k = keys[rng.randrange(n_clusters)]
            drawn_rows.extend(by[k])
        if not drawn_rows:
            continue
        s = sum(deltas[j] for j in drawn_rows) / len(drawn_rows)
        boots.append(s)
    boots.sort()
    r = len(boots)
    lo = boots[int(0.025 * r)] if r else point
    hi = boots[max(0, int(0.975 * r) - 1)] if r else point
    # also report naive row bootstrap for contrast (same seed stream offset)
    naive = paired_bootstrap_diff(baseline, candidate, reps=reps, seed=seed)
    return {
        "n": n,
        "n_clusters": n_clusters,
        "point_diff": point,
        "lo": lo,
        "hi": hi,
        "includes_zero": lo <= 0.0 <= hi,
        "baseline_rate": sum(b) / n,
        "candidate_rate": sum(c) / n,
        "method": "cluster_paired_bootstrap",
        "reps": reps,
        "naive_row_lo": naive["lo"],
        "naive_row_hi": naive["hi"],
        "naive_includes_zero": naive["includes_zero"],
        "width_ratio_vs_naive": ((hi - lo) / (naive["hi"] - naive["lo"])) if (naive["hi"] - naive["lo"]) else None,
        "sample_unit": "cluster",
        "fixture_status": "SIMULATED",
    }


def sequential_holm_looks(
    look_p_values: Sequence[Sequence[float]],
    *,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Sequential looks at a pre-specified family with Holm at spent alpha.

    At look t of T, spend alpha_t = alpha * t / T (simple linear spend).
    Apply Holm at alpha_t to the family observed at that look. Returns per-look
    decisions and whether any contrast crossed. Teaching fixture: SIMULATED
    p-value schedules supplied by the lab/tests.
    """
    if not look_p_values:
        raise ValueError("empty looks")
    T = len(look_p_values)
    looks = []
    stopped = False
    stop_look = None
    for t, pvals in enumerate(look_p_values, start=1):
        spent = alpha * (t / T)
        adj = holm_adjust(pvals)
        survivors = [row for row in adj if row["p_holm"] <= spent]
        decision = "STOP_REJECT" if survivors and not stopped else ("CONTINUE" if not stopped else "POST_STOP")
        if survivors and not stopped:
            stopped = True
            stop_look = t
        looks.append({
            "look": t,
            "T": T,
            "alpha_spent": spent,
            "holm": adj,
            "survivors": survivors,
            "decision": decision,
        })
    return {
        "alpha": alpha,
        "n_looks": T,
        "stopped": stopped,
        "stop_look": stop_look,
        "looks": looks,
        "method": "sequential_holm_linear_spend",
        "fixture_status": "SIMULATED",
    }
