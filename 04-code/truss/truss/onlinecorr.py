"""From offline scores to online outcomes (Chapter 35). Signature 8.

Correlate offline proxies with online signals, test surrogacy direction,
counterfactual logging stubs, and anti-correlation injection diagnosis.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


ONLINE_SIGNALS = (
    "resolution",
    "re_contact",
    "escalation",
    "complaint",
)


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 3:
        raise ValueError("need paired series length >= 3")
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def correlate_proxy_online(
    offline: Sequence[float],
    online: Sequence[float],
    *,
    name: str,
    signal: str,
) -> dict[str, Any]:
    r = pearson(offline, online)
    return {
        "proxy": name,
        "signal": signal,
        "n": len(offline),
        "r": round(r, 4),
        "predicts": abs(r) >= 0.35,
        "direction": "positive" if r > 0 else ("negative" if r < 0 else "flat"),
    }


def surrogacy_table(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """rows: proxy, signal, r, predicts."""
    return {
        "signature": 8,
        "rows": list(rows),
        "usable_proxies": [r["proxy"] for r in rows if r.get("predicts")],
        "failed_proxies": [r["proxy"] for r in rows if not r.get("predicts")],
    }


def counterfactual_log(
    trace_id: str,
    *,
    shown_arm: str,
    logged_alt_arms: Sequence[str],
    policy_hash: str,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "shown_arm": shown_arm,
        "logged_alt_arms": list(logged_alt_arms),
        "policy_hash": policy_hash,
        "complete": bool(logged_alt_arms) and bool(policy_hash),
    }


def anti_correlation_injection(
    proxy: Sequence[float],
    complaints: Sequence[float],
) -> dict[str, Any]:
    """Diagnose a proxy that rises while complaints rise (bad surrogate)."""
    r = pearson(proxy, complaints)
    return {
        "r": round(r, 4),
        "anti_correlated_with_harm": r > 0.2,
        "label": "BAD_PROXY" if r > 0.2 else "OK",
        "lesson": "A proxy that tracks compliments while complaints rise must not gate releases.",
    }


def online_signal_rates(events: Mapping[str, int], n_sessions: int) -> dict[str, Any]:
    if n_sessions <= 0:
        raise ValueError("n_sessions")
    out = {k: events.get(k, 0) / n_sessions for k in ONLINE_SIGNALS}
    out["n_sessions"] = n_sessions
    return out
