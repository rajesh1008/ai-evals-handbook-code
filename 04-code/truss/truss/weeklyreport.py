"""Weekly quality report for non-engineer readers (Chapter 40).

Builds a one-page hierarchy (decide → gate → monitor → inform), trend
series that can hide segment regressions when only the overall line is
read, and a rendered text artefact. All rates need explicit denominators.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

TIERS = ("decide", "gate", "monitor", "inform")


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion (k successes in n)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if k < 0 or k > n:
        raise ValueError("k out of range")
    phat = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = phat + z2 / (2 * n)
    margin = z * ((phat * (1 - phat) / n + z2 / (4 * n * n)) ** 0.5)
    return ((centre - margin) / denom, (centre + margin) / denom)


def metric_card(
    name: str,
    *,
    tier: str,
    failures: int,
    n: int,
    owner: str,
    action: str,
    target: float | None = None,
    unit: str = "rate",
) -> dict[str, Any]:
    """One metric with denominator, owner, action, and Wilson interval when rate."""
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS}")
    if n <= 0:
        raise ValueError("n must be positive")
    if failures < 0 or failures > n:
        raise ValueError("failures out of range")
    rate = failures / n
    lo, hi = _wilson(failures, n) if unit == "rate" else (None, None)
    return {
        "name": name,
        "tier": tier,
        "failures": failures,
        "n": n,
        "rate": rate,
        "wilson_lo": lo,
        "wilson_hi": hi,
        "owner": owner,
        "action": action,
        "target": target,
        "unit": unit,
        "meets_target": (hi is not None and target is not None and hi < target)
        if unit == "rate" and target is not None
        else None,
    }


def hierarchy_page(cards: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Group cards by tier in decide→inform order; refuse unknown tiers."""
    by: dict[str, list] = {t: [] for t in TIERS}
    for c in cards:
        t = c["tier"]
        if t not in by:
            raise ValueError(f"unknown tier {t}")
        by[t].append(dict(c))
    return {"tiers": TIERS, "by_tier": by, "n_cards": len(cards)}


def trend_point(
    week: str,
    *,
    overall_failures: int,
    overall_n: int,
    segments: Mapping[str, Mapping[str, int]],
) -> dict[str, Any]:
    """One week: overall rate plus named segment rates (each with n, failures)."""
    if overall_n <= 0:
        raise ValueError("overall_n must be positive")
    segs = {}
    for name, s in segments.items():
        fn, nn = int(s["failures"]), int(s["n"])
        if nn <= 0:
            raise ValueError(f"segment {name} n must be positive")
        segs[name] = {"failures": fn, "n": nn, "rate": fn / nn}
    return {
        "week": week,
        "overall": {
            "failures": overall_failures,
            "n": overall_n,
            "rate": overall_failures / overall_n,
        },
        "segments": segs,
    }


def overall_delta(series: Sequence[Mapping[str, Any]]) -> float:
    """Last overall rate minus first; negative means improvement for failure rates."""
    if len(series) < 2:
        raise ValueError("need at least two weeks")
    return series[-1]["overall"]["rate"] - series[0]["overall"]["rate"]


def segment_delta(series: Sequence[Mapping[str, Any]], segment: str) -> float:
    if len(series) < 2:
        raise ValueError("need at least two weeks")
    return series[-1]["segments"][segment]["rate"] - series[0]["segments"][segment]["rate"]


def hides_segment_regression(
    series: Sequence[Mapping[str, Any]],
    *,
    segment: str,
    overall_ok_if_delta_le: float = 0.0,
    segment_bad_if_delta_ge: float = 0.005,
) -> dict[str, Any]:
    """True when overall looks flat/better while a named segment regresses.

    This is the Chapter 40 failure injection: a trend line that hides a
    segment regression when the reader only watches the overall rate.
    """
    od = overall_delta(series)
    sd = segment_delta(series, segment)
    overall_looks_ok = od <= overall_ok_if_delta_le
    segment_regressed = sd >= segment_bad_if_delta_ge
    return {
        "segment": segment,
        "overall_delta": od,
        "segment_delta": sd,
        "overall_looks_ok": overall_looks_ok,
        "segment_regressed": segment_regressed,
        "hidden": overall_looks_ok and segment_regressed,
    }


def render_one_page(
    *,
    title: str,
    week_ending: str,
    hierarchy: Mapping[str, Any],
    headline: str,
    what_changed: Sequence[str],
    ask: Sequence[str],
    packet: Mapping[str, Any] | None = None,
) -> str:
    """Plain-text one-page artefact a non-engineer can act on in two minutes."""
    lines = [
        title,
        f"Week ending {week_ending}",
        "",
        "HEADLINE",
        headline,
        "",
        "METRIC HIERARCHY (decide → gate → monitor → inform)",
    ]
    for tier in hierarchy["tiers"]:
        cards = hierarchy["by_tier"].get(tier, [])
        lines.append(f"  [{tier.upper()}]")
        if not cards:
            lines.append("    (none this week)")
            continue
        for c in cards:
            if c.get("unit") == "rate":
                lo = c["wilson_lo"]
                hi = c["wilson_hi"]
                tgt = c.get("target")
                meet = c.get("meets_target")
                flag = "MEETS" if meet else ("OPEN" if meet is False else "n/a")
                lines.append(
                    f"    {c['name']}: {c['failures']}/{c['n']} = {c['rate']:.2%}"
                    f" (Wilson {lo:.2%}–{hi:.2%}; target {tgt}; {flag})"
                    f" — owner {c['owner']}; action {c['action']}"
                )
            else:
                lines.append(
                    f"    {c['name']}: {c.get('value', c.get('rate'))}"
                    f" — owner {c['owner']}; action {c['action']}"
                )
    lines.append("")
    lines.append("WHAT CHANGED")
    for w in what_changed:
        lines.append(f"  - {w}")
    lines.append("")
    lines.append("ASK / DECISION")
    for a in ask:
        lines.append(f"  - {a}")
    if packet:
        lines.append("")
        lines.append("INCIDENT→EVAL PACKET")
        for k, v in packet.items():
            lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("End of page.")
    return "\n".join(lines)


def slice_gate_row(
    slice_name: str,
    *,
    failures: int,
    n: int,
    gate: float,
) -> dict[str, Any]:
    rate = failures / n if n else 0.0
    lo, hi = _wilson(failures, n) if n else (0.0, 1.0)
    return {
        "slice": slice_name,
        "failures": failures,
        "n": n,
        "rate": rate,
        "wilson_hi": hi,
        "gate": gate,
        "holds": hi < gate if n else False,
    }
