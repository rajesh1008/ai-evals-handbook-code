"""Truss costknow (Chapter 41): eval cost lines, waterfalls, and denominators.

Version 0.44. Distinguishes invoice-actual charges, token-priced estimates,
worst-case unknown reserves, safety headroom, and SIM forecasts. Never invents
provider bills; callers supply verified unit costs.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


KIND_INVOICE = "invoice_actual"
KIND_TOKEN = "token_priced_estimate"
KIND_RESERVE = "unknown_reserve_worst_case"
KIND_HEADROOM = "safety_headroom"
KIND_SIM = "simulated_forecast"


def classify_line(
    *,
    amount_usd: float,
    kind: str,
    unit: str,
    currency: str = "USD",
    as_of: str,
    source: str,
) -> dict[str, Any]:
    """Name a cost line with its epistemic kind, unit, and primary source."""
    if kind not in {
        KIND_INVOICE,
        KIND_TOKEN,
        KIND_RESERVE,
        KIND_HEADROOM,
        KIND_SIM,
    }:
        raise ValueError(f"unknown cost kind: {kind}")
    if amount_usd < 0:
        raise ValueError("amount_usd must be non-negative")
    return {
        "amount_usd": float(amount_usd),
        "kind": kind,
        "unit": unit,
        "currency": currency,
        "as_of": as_of,
        "source": source,
    }


def study_ceiling(
    charged_usd: float,
    unreconciled_usd: float,
    headroom_usd: float,
) -> dict[str, float]:
    """Safe ceiling = charged + unknown reserves + safety headroom."""
    return {
        "charged_usd": float(charged_usd),
        "unreconciled_usd": float(unreconciled_usd),
        "headroom_usd": float(headroom_usd),
        "safe_ceiling_usd": float(charged_usd + unreconciled_usd + headroom_usd),
    }


def amortise_study(
    study_usd: float,
    n_releases_benefiting: int,
) -> dict[str, float]:
    """Sunk study cost vs incremental per-release share (accounting view)."""
    if n_releases_benefiting < 1:
        raise ValueError("n_releases_benefiting must be >= 1")
    share = study_usd / n_releases_benefiting
    return {
        "study_usd": float(study_usd),
        "n_releases": int(n_releases_benefiting),
        "amortised_per_release_usd": float(share),
        "note": "amortisation is an accounting allocation; the cash was spent once",
    }


def release_bill(
    *,
    call_usd: float,
    ordered_read_usd: float,
    ci_usd: float = 0.0,
    other_usd: float = 0.0,
) -> dict[str, float]:
    """Per-release eval bill: model calls + ordered human reads + CI + other."""
    total = call_usd + ordered_read_usd + ci_usd + other_usd
    return {
        "call_usd": float(call_usd),
        "ordered_read_usd": float(ordered_read_usd),
        "ci_usd": float(ci_usd),
        "other_usd": float(other_usd),
        "total_usd": float(total),
    }


def waterfall(
    steps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Cumulative cost after each named cut. Each step needs name + total_usd."""
    if not steps:
        raise ValueError("waterfall needs at least one step")
    rows = []
    for i, s in enumerate(steps):
        total = float(s["total_usd"])
        prev = float(steps[0]["total_usd"]) if i == 0 else float(steps[i - 1]["total_usd"])
        rows.append(
            {
                "step": i,
                "name": s["name"],
                "total_usd": total,
                "delta_usd": total - prev if i else 0.0,
                "kind": s.get("kind", KIND_SIM),
            }
        )
    return {
        "steps": rows,
        "start_usd": rows[0]["total_usd"],
        "end_usd": rows[-1]["total_usd"],
        "saved_usd": rows[0]["total_usd"] - rows[-1]["total_usd"],
    }


def cheap_first_cascade(
    volumes: Mapping[str, int],
    unit_costs: Mapping[str, float],
) -> dict[str, Any]:
    """Cost a cascade: deterministic → small judge → human read.

    volumes keys: n_traces, n_after_deterministic, n_ordered_reads
    unit_costs keys: deterministic, small_judge, human_read
    """
    n = int(volumes["n_traces"])
    n_judge = int(volumes["n_after_deterministic"])
    n_read = int(volumes["n_ordered_reads"])
    c_det = float(unit_costs["deterministic"])
    c_judge = float(unit_costs["small_judge"])
    c_read = float(unit_costs["human_read"])
    parts = {
        "deterministic_usd": n * c_det,
        "judge_usd": n_judge * c_judge,
        "read_usd": n_read * c_read,
    }
    parts["total_usd"] = sum(parts.values())
    parts["n_traces"] = n
    parts["n_after_deterministic"] = n_judge
    parts["n_ordered_reads"] = n_read
    return parts


def sample_by_risk(
    strata: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Allocate sample size by risk weight, not traffic share.

    Each stratum: name, traffic_share, risk_weight, unit_cost_usd.
    Returns draws and expected cost under a fixed budget of draws.
    """
    wsum = sum(float(s["risk_weight"]) for s in strata)
    if wsum <= 0:
        raise ValueError("risk weights must sum > 0")
    rows = []
    for s in strata:
        share = float(s["risk_weight"]) / wsum
        rows.append(
            {
                "name": s["name"],
                "traffic_share": float(s["traffic_share"]),
                "risk_weight": float(s["risk_weight"]),
                "draw_share": share,
                "unit_cost_usd": float(s["unit_cost_usd"]),
            }
        )
    return {"strata": rows, "weight_sum": wsum}


def bias_battery_gate(
    *,
    tpr: float,
    tnr: float,
    position_flip_rate: float,
    tpr_floor: float = 0.80,
    tnr_floor: float = 0.90,
    flip_ceiling: float = 0.05,
) -> dict[str, Any]:
    """Admit a cheap judge only if accuracy floors and bias battery clear."""
    clears = (
        tpr >= tpr_floor
        and tnr >= tnr_floor
        and position_flip_rate <= flip_ceiling
    )
    return {
        "tpr": float(tpr),
        "tnr": float(tnr),
        "position_flip_rate": float(position_flip_rate),
        "tpr_floor": tpr_floor,
        "tnr_floor": tnr_floor,
        "flip_ceiling": flip_ceiling,
        "admit": bool(clears),
        "failed_bias_battery": bool(position_flip_rate > flip_ceiling),
    }


def cost_per_decision(
    total_usd: float,
    n_decisions: int,
) -> dict[str, float]:
    if n_decisions < 1:
        raise ValueError("n_decisions must be >= 1")
    return {
        "total_usd": float(total_usd),
        "n_decisions": int(n_decisions),
        "usd_per_decision": float(total_usd) / n_decisions,
    }
