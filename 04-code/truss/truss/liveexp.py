"""Truss liveexp: live A/B assignment, sequential peeks, guardrails, interleaving."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Sequence
import hashlib, math, random

def _wilson_upper(k: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 1.0
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = p + z2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return (centre + margin) / denom

def assign_unit(unit_id: str, salt: str, arms: Sequence[str] = ("control", "treatment")) -> str:
    h = hashlib.sha256(f"{salt}:{unit_id}".encode()).hexdigest()
    return arms[int(h[:8], 16) % len(arms)]

@dataclass
class PeekResult:
    look: int
    n_control: int
    n_treatment: int
    k_control: int
    k_treatment: int
    delta: float
    p_approx: float
    continue_: bool

def sequential_peeks(
    control_outcomes: Sequence[int],
    treatment_outcomes: Sequence[int],
    alpha_spend: Sequence[float],
    looks_at: Sequence[int],
) -> list[dict[str, Any]]:
    """Simple alpha-spending peeks on a rate difference (treatment - control errors)."""
    out = []
    for look, (n, a) in enumerate(zip(looks_at, alpha_spend), start=1):
        c = control_outcomes[:n]
        t = treatment_outcomes[:n]
        kc, kt = sum(c), sum(t)
        nc, nt = len(c), len(t)
        pc = kc / nc if nc else 0.0
        pt = kt / nt if nt else 0.0
        delta = pt - pc
        # normal approx two-sided p for teaching
        se = math.sqrt(max(pc * (1 - pc) / max(nc, 1) + pt * (1 - pt) / max(nt, 1), 1e-12))
        z = abs(delta) / se if se > 0 else 0.0
        # crude two-sided p from erfc
        p = math.erfc(z / math.sqrt(2))
        stop_for_efficacy = p < a and delta < 0  # treatment better (fewer errors)
        out.append({
            "look": look,
            "n_per_arm": n,
            "k_control": kc,
            "k_treatment": kt,
            "rate_control": pc,
            "rate_treatment": pt,
            "delta": delta,
            "alpha_spend": a,
            "p_approx": p,
            "stop_efficacy": stop_for_efficacy,
            "continue": not stop_for_efficacy,
        })
    return out

def guardrail_trip(
    k_errors: int,
    n: int,
    target: float = 0.005,
    z: float = 1.645,
) -> dict[str, Any]:
    upper = _wilson_upper(k_errors, n, z=z)
    return {
        "k": k_errors,
        "n": n,
        "rate": k_errors / n if n else 0.0,
        "target": target,
        "wilson_upper": upper,
        "trip": upper > target and k_errors > 0 or (n >= 50 and k_errors / max(n, 1) > target),
        # trip if upper bound clears target badly OR raw rate exceeds with enough n
        "trip_reason": None,
    }

def refine_guardrail(k: int, n: int, target: float = 0.005) -> dict[str, Any]:
    g = guardrail_trip(k, n, target=target)
    # Harbor teaching: never trip on zero errors; trip on clear rate spikes.
    trip = False
    reason = "ok"
    if k == 0:
        trip = False
        reason = "ok_zero_errors"
    elif n >= 40 and (k / n) > target * 2:
        trip = True
        reason = "rate_spike"
    elif n >= 100 and k >= 3 and g["wilson_upper"] > target * 2:
        trip = True
        reason = "upper_bound"
    g["trip"] = trip
    g["trip_reason"] = reason
    return g

def interleave_rankings(
    control_ranking: Sequence[str],
    treatment_ranking: Sequence[str],
    clicks: Sequence[str],
) -> dict[str, Any]:
    """Team-draft interleaving credit for clicked docs."""
    seen = set()
    interleaved = []
    i = j = 0
    turn = 0
    while len(interleaved) < max(len(control_ranking), len(treatment_ranking)):
        if turn % 2 == 0 and i < len(control_ranking):
            d = control_ranking[i]; i += 1
            if d not in seen:
                interleaved.append(("control", d)); seen.add(d)
        elif j < len(treatment_ranking):
            d = treatment_ranking[j]; j += 1
            if d not in seen:
                interleaved.append(("treatment", d)); seen.add(d)
        elif i < len(control_ranking):
            d = control_ranking[i]; i += 1
            if d not in seen:
                interleaved.append(("control", d)); seen.add(d)
        else:
            break
        turn += 1
    credit = {"control": 0, "treatment": 0}
    click_set = set(clicks)
    for arm, doc in interleaved:
        if doc in click_set:
            credit[arm] += 1
    return {
        "interleaved": interleaved,
        "credit": credit,
        "winner": "treatment" if credit["treatment"] > credit["control"] else (
            "control" if credit["control"] > credit["treatment"] else "tie"
        ),
    }

def experiment_record(
    experiment_id: str,
    unit: str,
    salt: str,
    arms: dict[str, str],
    guardrail_metric: str,
    primary_metric: str,
    status: str,
) -> dict[str, Any]:
    return {
        "experiment_id": experiment_id,
        "unit_of_randomisation": unit,
        "salt": salt,
        "arms": arms,
        "primary_metric": primary_metric,
        "guardrail_metric": guardrail_metric,
        "status": status,
    }
