"""Truss 0.31 reviewer analytics (Chapter 28; book name Truss v4.5).

Override rate, approval-time summaries, agreement with gold, automation-bias
detection rate, fatigue-by-position curves, second-review sampling helpers.
Callers label SIMULATED reviewer fixtures; never claim real-human rates without evidence.
"""
from __future__ import annotations
from collections import defaultdict
from statistics import median
from typing import Any, Sequence


def override_rate(rows: Sequence[dict]) -> dict[str, Any]:
    """Fraction of reviews where the human changed the model recommendation."""
    n = len(rows)
    ov = sum(1 for r in rows if r.get("overrode"))
    return {"n": n, "n_override": ov, "override_rate": ov / n if n else 0.0}


def approval_time_summary(seconds: Sequence[float]) -> dict[str, Any]:
    xs = sorted(float(s) for s in seconds)
    n = len(xs)
    if not n:
        return {"n": 0, "median": None, "p10": None, "p90": None}
    def pct(p):
        i = min(n - 1, max(0, int(round((p / 100) * (n - 1)))))
        return xs[i]
    return {"n": n, "median": median(xs), "p10": pct(10), "p90": pct(90)}


def agreement_with_gold(rows: Sequence[dict]) -> dict[str, Any]:
    n = len(rows)
    ok = sum(1 for r in rows if r.get("human_label") == r.get("gold"))
    return {"n": n, "n_agree": ok, "agreement": ok / n if n else 0.0}


def per_reviewer_table(rows: Sequence[dict]) -> list[dict[str, Any]]:
    by: dict[str, list] = defaultdict(list)
    for r in rows:
        by[str(r.get("reviewer_id", "?"))].append(r)
    out = []
    for rid, rs in sorted(by.items()):
        ov = override_rate(rs)
        times = [r["approval_seconds"] for r in rs if "approval_seconds" in r]
        ag = agreement_with_gold(rs)
        out.append({
            "reviewer_id": rid,
            "n": len(rs),
            "override_rate": ov["override_rate"],
            "median_approval_seconds": approval_time_summary(times)["median"],
            "agreement": ag["agreement"],
        })
    return out


def automation_bias_rate(rows: Sequence[dict]) -> dict[str, Any]:
    """Among cases where gold disagrees with AI and human saw AI advice,
    fraction where human followed the wrong AI."""
    eligible = [r for r in rows if r.get("ai_wrong") and r.get("saw_ai") and r.get("gold") is not None]
    n = len(eligible)
    biased = sum(1 for r in eligible if r.get("human_label") == r.get("ai_label") and r.get("human_label") != r.get("gold"))
    return {"n_eligible": n, "n_biased": biased, "automation_bias_rate": biased / n if n else 0.0}


def fatigue_curve(rows: Sequence[dict], bins: int = 5) -> list[dict[str, Any]]:
    """Agreement by queue-position quintile (0=earliest)."""
    if not rows:
        return []
    ordered = sorted(rows, key=lambda r: r.get("queue_position", 0))
    n = len(ordered)
    out = []
    for b in range(bins):
        lo = int(b * n / bins)
        hi = int((b + 1) * n / bins)
        chunk = ordered[lo:hi]
        ag = agreement_with_gold(chunk)
        out.append({"bin": b, "n": len(chunk), "agreement": ag["agreement"],
                    "mean_position": sum(r.get("queue_position", 0) for r in chunk) / max(1, len(chunk))})
    return out


def post_review_error_rate(rows: Sequence[dict]) -> dict[str, Any]:
    """Errors remaining after human review versus gold."""
    n = len(rows)
    err = sum(1 for r in rows if r.get("final_label") != r.get("gold"))
    return {"n": n, "n_error": err, "post_review_error_rate": err / n if n else 0.0}


def second_review_sample(rows: Sequence[dict], k: int, seed: int = 2026) -> list[dict]:
    import random
    rng = random.Random(seed)
    pool = list(rows)
    rng.shuffle(pool)
    return pool[: min(k, len(pool))]
