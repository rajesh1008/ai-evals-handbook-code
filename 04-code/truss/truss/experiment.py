"""Truss experiment registry (Chapter 42 / book Truss v7).

Deterministic helpers for paired comparative evals. No network.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple
import hashlib
import json
import math


def _wilson(successes: int, n: int, z: float = 1.96) -> Dict[str, float]:
    if n <= 0:
        raise ValueError("n must be positive")
    if successes < 0 or successes > n:
        raise ValueError("successes out of range")
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return {"lo": max(0.0, centre - margin), "hi": min(1.0, centre + margin), "p": p}


def paired_table(
    systems: Mapping[str, Sequence[int]],
    *,
    fail_is_one: bool = True,
) -> Dict[str, Any]:
    """systems: name -> binary outcomes aligned on the same trace ids (1=fail if fail_is_one)."""
    names = list(systems)
    if not names:
        raise ValueError("no systems")
    n = len(systems[names[0]])
    if n == 0:
        raise ValueError("empty")
    for name in names:
        if len(systems[name]) != n:
            raise ValueError(f"length mismatch for {name}")
    rows = []
    for name in names:
        fails = int(sum(1 for x in systems[name] if (x == 1 if fail_is_one else x == 0)))
        w = _wilson(fails, n)
        rows.append(
            {
                "system": name,
                "failures": fails,
                "n": n,
                "error_rate": fails / n,
                "wilson_lo": w["lo"],
                "wilson_hi": w["hi"],
            }
        )
    ranked = sorted(rows, key=lambda r: (r["error_rate"], r["wilson_hi"], r["system"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return {"n": n, "rows": ranked, "ranking": [r["system"] for r in ranked]}


def unpaired_resample_rank(
    systems: Mapping[str, Sequence[int]],
    *,
    seed: int,
    take: int | None = None,
) -> Dict[str, Any]:
    """Deliberately unfair convenience confound: each system on a different subsample."""
    import random

    rng = random.Random(seed)
    names = list(systems)
    n = len(systems[names[0]])
    k = take or max(1, n // 2)
    unfair: Dict[str, List[int]] = {}
    for i, name in enumerate(names):
        start = (i * 97 + seed) % max(1, n - k + 1)
        idx = list(range(start, start + k))
        unfair[name] = [systems[name][j] for j in idx]
    table = paired_table(unfair)
    table["mode"] = "unpaired_subsample"
    table["take"] = k
    return table


def n_pairwise_comparisons(n_systems: int) -> int:
    if n_systems < 2:
        raise ValueError("need >=2 systems")
    return n_systems * (n_systems - 1) // 2


def n_vs_control_comparisons(n_systems: int) -> int:
    """Number of tests when each non-control system is compared to one fixed control."""
    if n_systems < 2:
        raise ValueError("need >=2 systems")
    return n_systems - 1


def multiple_comparison_note(
    n_comparisons: int,
    alpha: float = 0.05,
    *,
    structure: str = "declared",
    n_systems: int | None = None,
    discarded_hypotheses: int = 0,
) -> Dict[str, Any]:
    """Bonferroni split by number of *hypothesis tests*, not number of systems.

    structure examples: "all_pairs", "vs_control", "custom".
    discarded_hypotheses: tests searched then omitted from the report — still count in the family.
    """
    if n_comparisons < 1:
        raise ValueError("need >=1 comparison")
    if discarded_hypotheses < 0:
        raise ValueError("discarded_hypotheses must be >=0")
    family_tests = n_comparisons + discarded_hypotheses
    return {
        "n_comparisons": n_comparisons,
        "discarded_hypotheses": discarded_hypotheses,
        "family_tests": family_tests,
        "n_systems": n_systems,
        "structure": structure,
        "family_alpha": alpha,
        "per_comparison_alpha": alpha / family_tests,
        "rule": "bonferroni_split",
        "controls": "family_wise_error_rate",
        "note_holm": "Holm also controls FWER (step-down); not interchangeable with BH",
        "note_bh": "Benjamini–Hochberg controls false-discovery rate (FDR), not FWER",
    }


def discordant_counts(
    a: Sequence[int],
    b: Sequence[int],
    *,
    fail_is_one: bool = True,
) -> Dict[str, int]:
    """2x2 paired failure counts for binary outcomes aligned on the same ids."""
    if len(a) != len(b):
        raise ValueError("length mismatch")
    n11 = n10 = n01 = n00 = 0
    for x, y in zip(a, b):
        fx = x == 1 if fail_is_one else x == 0
        fy = y == 1 if fail_is_one else y == 0
        if fx and fy:
            n11 += 1
        elif fx and not fy:
            n10 += 1
        elif (not fx) and fy:
            n01 += 1
        else:
            n00 += 1
    return {"n11": n11, "n10": n10, "n01": n01, "n00": n00, "n": len(a), "discordant": n10 + n01}


def mcnemar_exact(
    n10: int,
    n01: int,
) -> Dict[str, Any]:
    """Exact two-sided McNemar test on discordant counts (binomial under p=0.5).

    Uses the classical exact form: 2 * sum_{k=0}^{min(n10,n01)} C(n,k) / 2^n.
    Assumptions: paired binary outcomes; independence across pairs; under H0 of
    equal marginal failure probabilities the discordant direction is fair coin.
    Does not establish equivalence; small discordant n yields low power.
    """
    if n10 < 0 or n01 < 0:
        raise ValueError("discordant counts must be non-negative")
    n = n10 + n01
    if n == 0:
        return {
            "n10": n10,
            "n01": n01,
            "n_discordant": 0,
            "p_value_exact": 1.0,
            "method": "mcnemar_exact_binomial",
            "null": "equal_marginal_failure_prob",
        }
    obs = min(n10, n01)
    # avoid float overflow for modest n via iterative product
    # P(K=k) = C(n,k) / 2^n
    # compute cumulative for k=0..obs
    # C(n,k)/2^n recursively
    total = 0.0
    term = 1.0  # C(n,0)/1 then we divide by 2^n at end... better: start C(n,0)=1
    # term_k = C(n,k)
    ck = 1
    for k in range(0, obs + 1):
        if k > 0:
            ck = ck * (n - k + 1) // k
        total += ck
    p = min(1.0, 2.0 * total / (2 ** n))
    return {
        "n10": n10,
        "n01": n01,
        "n_discordant": n,
        "p_value_exact": p,
        "method": "mcnemar_exact_binomial",
        "null": "equal_marginal_failure_prob",
    }


def paired_contrast(
    a: Sequence[int],
    b: Sequence[int],
    *,
    name_a: str = "a",
    name_b: str = "b",
    fail_is_one: bool = True,
) -> Dict[str, Any]:
    """Worked paired contrast: discordant 2x2 + exact McNemar + marginal rates."""
    d = discordant_counts(a, b, fail_is_one=fail_is_one)
    m = mcnemar_exact(d["n10"], d["n01"])
    fa = sum(1 for x in a if (x == 1 if fail_is_one else x == 0))
    fb = sum(1 for x in b if (x == 1 if fail_is_one else x == 0))
    n = d["n"]
    wa = _wilson(fa, n)
    wb = _wilson(fb, n)
    return {
        "system_a": name_a,
        "system_b": name_b,
        "failures_a": fa,
        "failures_b": fb,
        "error_rate_a": fa / n,
        "error_rate_b": fb / n,
        "wilson_a": wa,
        "wilson_b": wb,
        "table": d,
        "mcnemar": m,
        "wilson_intervals_overlap": not (wa["hi"] < wb["lo"] or wb["hi"] < wa["lo"]),
        "teaching": (
            "Overlapping marginal Wilson intervals are not a paired test and "
            "do not establish equivalence or significance of the difference."
        ),
    }



def router_component_card(
    *,
    route_accuracy: float,
    oracle_accuracy: float,
    cost_per_query_usd: float,
    n: int,
    owner: str,
) -> Dict[str, Any]:
    gap = oracle_accuracy - route_accuracy
    return {
        "component": "router",
        "route_accuracy": route_accuracy,
        "oracle_accuracy": oracle_accuracy,
        "gap_to_oracle": gap,
        "cost_per_query_usd": cost_per_query_usd,
        "n": n,
        "owner": owner,
        "plateau_flag": gap > 0.05,
    }


def register_experiment(
    *,
    experiment_id: str,
    systems: Sequence[str],
    n_paired: int,
    digest: str,
    hypothesis: str,
    owner: str,
) -> Dict[str, Any]:
    if not experiment_id or not systems:
        raise ValueError("experiment_id and systems required")
    payload = {
        "experiment_id": experiment_id,
        "systems": list(systems),
        "n_paired": n_paired,
        "digest": digest,
        "hypothesis": hypothesis,
        "owner": owner,
        "schema": "truss.experiment.v1",
    }
    raw = json.dumps(payload, sort_keys=True).encode()
    payload["record_sha12"] = hashlib.sha256(raw).hexdigest()[:12]
    return payload


def frontier_points(
    systems: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """systems items need error_rate and cost_usd_per_1k."""
    pts = []
    for s in systems:
        pts.append(
            {
                "system": s["system"],
                "error_rate": float(s["error_rate"]),
                "cost_usd_per_1k": float(s["cost_usd_per_1k"]),
            }
        )
    pts_sorted = sorted(pts, key=lambda p: (p["cost_usd_per_1k"], p["error_rate"]))
    pareto = []
    best_err = float("inf")
    for p in pts_sorted:
        if p["error_rate"] < best_err:
            pareto.append({**p, "on_frontier": True})
            best_err = p["error_rate"]
        else:
            pareto.append({**p, "on_frontier": False})
    return pareto
