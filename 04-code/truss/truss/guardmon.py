"""Guardrails, monitoring and evals as one family (Chapter 37).

Promote deterministic checks to in-flight guards, evaluate guard precision /
recall / over-blocking, detect vocabulary over-refusal, and catch latency
budgets that break channel timeouts (SMS).
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


TIERS = ("pre_deploy", "in_flight", "post_hoc")
SMS_TIMEOUT_MS = 2000


def promote_check_to_guard(
    check_name: str,
    *,
    latency_budget_ms: int,
    tier: str = "in_flight",
) -> dict[str, Any]:
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS}")
    if latency_budget_ms <= 0:
        raise ValueError("latency_budget_ms must be positive")
    return {
        "check": check_name,
        "tier": tier,
        "latency_budget_ms": latency_budget_ms,
        "promoted": True,
        "kind": "deterministic_guard",
    }


def run_guard(
    guard: Mapping[str, Any],
    *,
    signal_pass: bool,
    latency_ms: float,
) -> dict[str, Any]:
    budget = int(guard["latency_budget_ms"])
    timed_out = latency_ms > budget
    if timed_out:
        decision = "timeout"
    elif signal_pass:
        decision = "pass"
    else:
        decision = "block"
    return {
        "check": guard["check"],
        "decision": decision,
        "latency_ms": round(float(latency_ms), 2),
        "budget_ms": budget,
        "timed_out": timed_out,
    }


def latency_breaks_channel(
    p99_latency_ms: float,
    *,
    channel_timeout_ms: int = SMS_TIMEOUT_MS,
) -> dict[str, Any]:
    breaks = p99_latency_ms > channel_timeout_ms
    return {
        "p99_latency_ms": round(float(p99_latency_ms), 2),
        "channel_timeout_ms": channel_timeout_ms,
        "breaks_timeout": breaks,
        "label": "SMS_TIMEOUT_BREAK" if breaks else "WITHIN_BUDGET",
    }


def evaluate_guard(
    preds: Sequence[str],
    gold: Sequence[str],
    *,
    block_label: str = "block",
    risky_label: str = "risky",
) -> dict[str, Any]:
    """preds/gold aligned; gold is 'risky' or 'benign'; preds 'block' or 'pass'."""
    if len(preds) != len(gold) or not preds:
        raise ValueError("preds and gold must be same non-empty length")
    tp = fp = tn = fn = 0
    for p, g in zip(preds, gold):
        blocked = p == block_label
        risky = g == risky_label
        if blocked and risky:
            tp += 1
        elif blocked and not risky:
            fp += 1
        elif (not blocked) and (not risky):
            tn += 1
        else:
            fn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    over_block = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "n": len(preds),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "over_block_rate": round(over_block, 4),
    }


def vocabulary_overrefuse(
    cases: Sequence[Mapping[str, Any]],
    *,
    scary_words: Sequence[str],
) -> dict[str, Any]:
    """Benign cases that contain scary surface words but should pass."""
    scary = [w.lower() for w in scary_words]
    hits = []
    for c in cases:
        text = str(c.get("text", "")).lower()
        blocked = bool(c.get("blocked"))
        benign = c.get("gold") == "benign"
        if benign and blocked and any(w in text for w in scary):
            hits.append(c.get("id"))
    n_benign_scary = sum(
        1
        for c in cases
        if c.get("gold") == "benign"
        and any(w in str(c.get("text", "")).lower() for w in scary)
    )
    rate = (len(hits) / n_benign_scary) if n_benign_scary else 0.0
    return {
        "scary_words": list(scary_words),
        "n_benign_scary": n_benign_scary,
        "n_overrefuse": len(hits),
        "overrefuse_rate": round(rate, 4),
        "example_ids": hits[:8],
    }


def sample_production_for_slow_eval(
    n_available: int,
    *,
    sample_n: int,
    seed: int,
) -> dict[str, Any]:
    if sample_n > n_available:
        raise ValueError("sample_n exceeds available")
    # deterministic pick without importing random module state globally
    step = max(1, n_available // sample_n)
    start = seed % max(1, step)
    ids = [f"prod-{(start + i * step) % n_available:06d}" for i in range(sample_n)]
    return {"n_available": n_available, "sample_n": sample_n, "seed": seed, "ids": ids}


def timeline_placement() -> list[dict[str, str]]:
    return [
        {"when": "pre_deploy", "family": "eval", "example": "PR fast/slow suite"},
        {"when": "in_flight", "family": "guard", "example": "hardship offer schema guard"},
        {"when": "post_hoc", "family": "monitor", "example": "weekly behaviour alert sample"},
    ]


def hardship_guard_coverage(n_offers: int, n_guarded: int) -> dict[str, Any]:
    if n_offers <= 0:
        raise ValueError("n_offers must be positive")
    rate = n_guarded / n_offers
    return {
        "n_offers": n_offers,
        "n_guarded": n_guarded,
        "coverage": round(rate, 4),
        "meets_100pct": n_guarded == n_offers,
    }
