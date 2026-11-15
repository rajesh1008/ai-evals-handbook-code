"""Truss gateway / migration eval helpers (Chapter 30).

Pinned model records, migration delta tables, mid-run upgrade detection,
silent-change canaries, deprecation plans and judge re-validation triggers.
Lab fixtures are SIMULATED unless a caller marks REAL API rows.
"""
from __future__ import annotations
from typing import Any, Sequence


def pin_record(model_id: str, provider: str, pinned_at: str, digest: str) -> dict[str, Any]:
    return {"model_id": model_id, "provider": provider, "pinned_at": pinned_at, "digest": digest}


def migration_delta(baseline: dict[str, float], candidate: dict[str, float]) -> dict[str, Any]:
    """Per-metric deltas candidate - baseline."""
    keys = sorted(set(baseline) | set(candidate))
    rows = []
    for k in keys:
        b = float(baseline.get(k, 0.0))
        c = float(candidate.get(k, 0.0))
        rows.append({"metric": k, "baseline": b, "candidate": c, "delta": c - b})
    improved = sum(1 for r in rows if r["delta"] > 0)
    regressed = sum(1 for r in rows if r["delta"] < 0)
    return {"rows": rows, "n_improved": improved, "n_regressed": regressed}


def release_decision(deltas: Sequence[dict], hold_on_any_regression: bool = True) -> dict[str, Any]:
    regs = [r for r in deltas if r.get("delta", 0) < 0]
    if hold_on_any_regression and regs:
        return {"decision": "HOLD", "reason": "regression", "regressions": regs}
    return {"decision": "SHIP", "reason": "no_hold_regressions", "regressions": []}


def midrun_upgrade_detect(run_models: Sequence[str]) -> dict[str, Any]:
    """True if more than one distinct model id appears in a single eval run."""
    uniq = sorted(set(run_models))
    return {
        "n_models": len(uniq),
        "models": uniq,
        "midrun_upgrade": len(uniq) > 1,
        "first": run_models[0] if run_models else None,
        "last": run_models[-1] if run_models else None,
    }


def silent_change_score(canary_repeats: Sequence[dict]) -> dict[str, Any]:
    """canary_repeats: list of {label, score} on frozen canary; flip if score changes."""
    if not canary_repeats:
        return {"n": 0, "n_flip": 0, "flip_rate": 0.0}
    # group by label
    by = {}
    for r in canary_repeats:
        by.setdefault(r["label"], []).append(r["score"])
    flips = 0
    for scores in by.values():
        if len(set(scores)) > 1:
            flips += 1
    n = len(by)
    return {"n": n, "n_flip": flips, "flip_rate": flips / n if n else 0.0}


def deprecation_plan(notice_days: int, suite_ready: bool, migration_hold: bool) -> dict[str, Any]:
    ok = notice_days >= 60 and suite_ready and not migration_hold
    return {
        "notice_days": notice_days,
        "suite_ready": suite_ready,
        "migration_hold": migration_hold,
        "accept_cutover": ok,
        "status": "READY" if ok else "NOT_READY",
    }


def judge_revalidation_triggers(model_changed: bool, prompt_changed: bool, policy_changed: bool, flip_rate: float, flip_floor: float = 0.05) -> dict[str, Any]:
    triggers = []
    if model_changed:
        triggers.append("model")
    if prompt_changed:
        triggers.append("prompt")
    if policy_changed:
        triggers.append("policy")
    if flip_rate >= flip_floor:
        triggers.append("canary_flip")
    return {"triggers": triggers, "must_revalidate": bool(triggers)}
