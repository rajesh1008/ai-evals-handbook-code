"""Truss 0.28 simulated-user and multi-turn metrics (Chapter 25).

Goal completion, turns to resolution, abandonment, persona pushback rate,
simulator-vs-real fidelity tables, and perturbation survival. SIMULATED
conversations are labelled as such by the caller; this module only scores.
"""
from __future__ import annotations
from collections import Counter
from typing import Any, Iterable, Sequence


def goal_completed(turns: Sequence[dict], *, goal_key: str = "goal_met") -> bool:
    """True when the final turn (or any turn) marks the user goal met."""
    if not turns:
        return False
    if any(t.get(goal_key) for t in turns):
        return True
    return bool(turns[-1].get("outcome") == "resolved")


def turns_to_resolution(turns: Sequence[dict]) -> int | None:
    """1-indexed turn count at first resolution; None if unresolved."""
    for i, t in enumerate(turns, 1):
        if t.get("goal_met") or t.get("outcome") == "resolved":
            return i
    return None


def abandoned(turns: Sequence[dict], *, max_turns: int = 12) -> bool:
    """True if the user left without resolution (explicit abandon or hung)."""
    if not turns:
        return True
    if any(t.get("outcome") == "abandoned" or t.get("abandoned") for t in turns):
        return True
    if turns_to_resolution(turns) is None and len(turns) >= max_turns:
        return True
    return False


def pushback_rate(turns: Sequence[dict]) -> dict[str, Any]:
    """Share of user turns that challenge or correct the assistant."""
    user = [t for t in turns if t.get("role") == "user"]
    push = [t for t in user if t.get("pushback")]
    n = len(user)
    return {"n_user": n, "n_pushback": len(push), "rate": (len(push) / n) if n else 0.0}


def fidelity_table(sim_stats: dict, real_stats: dict, keys: Sequence[str] | None = None) -> dict:
    """Side-by-side simulator vs real transcript stats for named keys."""
    keys = list(keys or sorted(set(sim_stats) | set(real_stats)))
    rows = []
    for k in keys:
        s, r = sim_stats.get(k), real_stats.get(k)
        gap = None
        if isinstance(s, (int, float)) and isinstance(r, (int, float)):
            gap = s - r
        rows.append({"key": k, "sim": s, "real": r, "gap": gap})
    return {"rows": rows}


def perturbation_survive(before_ok: bool, after_ok: bool) -> dict[str, Any]:
    """Whether a conversation still succeeds after a mid-session perturbation."""
    return {
        "before_ok": before_ok,
        "after_ok": after_ok,
        "survived": bool(before_ok and after_ok),
        "regressed": bool(before_ok and not after_ok),
        "rescued": bool((not before_ok) and after_ok),
    }


def aggregate_conversations(convs: Iterable[dict]) -> dict[str, Any]:
    """Roll up goal completion, mean turns, abandonment, mean pushback."""
    convs = list(convs)
    n = len(convs)
    done = sum(1 for c in convs if c.get("goal_completed"))
    aband = sum(1 for c in convs if c.get("abandoned"))
    turns = [c["turns_to_resolution"] for c in convs if c.get("turns_to_resolution") is not None]
    push = [c.get("pushback_rate", 0.0) for c in convs]
    return {
        "n": n,
        "goal_completion": done / n if n else 0.0,
        "n_completed": done,
        "abandonment": aband / n if n else 0.0,
        "n_abandoned": aband,
        "mean_turns_to_resolution": (sum(turns) / len(turns)) if turns else None,
        "mean_pushback_rate": (sum(push) / len(push)) if push else 0.0,
    }


def polite_mask_failure(pushback_rate_value: float, *, floor: float = 0.05) -> bool:
    """True when a too-polite simulator (near-zero pushback) can hide a real fail."""
    return pushback_rate_value < floor
