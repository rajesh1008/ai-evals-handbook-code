"""Evals in the pull request (Chapter 34). Truss v5 PR gate ladder.

Deterministic checks before judges, fast vs slow suites, flake quarantine,
cost accounting, promotion ladder (Signature 9), and CI workflow records.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


LADDER_STEPS = (
    "deterministic",
    "fast_suite",
    "slow_suite",
    "canary",
    "full_traffic",
)


def deterministic_checks(case: Mapping[str, Any]) -> dict[str, Any]:
    """Schema / pattern / status / similarity-style checks before any judge."""
    fails = []
    if not case.get("schema_ok", True):
        fails.append("schema")
    if not case.get("pattern_ok", True):
        fails.append("pattern")
    if case.get("status") not in (None, "ok", "pass"):
        fails.append("status")
    sim = case.get("similarity")
    if sim is not None and float(sim) < float(case.get("similarity_floor", 0.7)):
        fails.append("similarity")
    return {"pass": not fails, "fails": fails}


def run_suite(cases: Sequence[Mapping[str, Any]], *, mode: str) -> dict[str, Any]:
    """Run a named suite. Fast mode uses only deterministic; slow adds judge_ok."""
    if mode not in ("fast", "slow"):
        raise ValueError("mode")
    rows = []
    for c in cases:
        det = deterministic_checks(c)
        ok = det["pass"]
        if mode == "slow" and ok:
            ok = bool(c.get("judge_ok", True))
        rows.append({"id": c.get("id"), "det": det, "ok": ok, "flake": bool(c.get("flake", False))})
    n = len(rows)
    n_pass = sum(1 for r in rows if r["ok"])
    return {
        "mode": mode,
        "n": n,
        "n_pass": n_pass,
        "pass_rate": (n_pass / n) if n else 0.0,
        "rows": rows,
    }


def flake_rate(repeats: Sequence[bool]) -> dict[str, Any]:
    if len(repeats) < 2:
        raise ValueError("need repeats")
    flips = sum(1 for i in range(1, len(repeats)) if repeats[i] != repeats[i - 1])
    # ever-fail among runs that also ever-pass
    ever_pass = any(repeats)
    ever_fail = not all(repeats)
    rate = sum(1 for x in repeats if not x) / len(repeats)
    return {
        "n": len(repeats),
        "fail_rate": rate,
        "flip_transitions": flips,
        "quarantine": rate > 0.10 and ever_pass and ever_fail,
    }


def quarantine(cases: Sequence[Mapping[str, Any]], *, flake_floor: float = 0.10) -> dict[str, Any]:
    blocked = []
    kept = []
    for c in cases:
        fr = float(c.get("flake_rate", 0.0))
        if fr > flake_floor:
            blocked.append(c.get("id"))
        else:
            kept.append(c.get("id"))
    return {"flake_floor": flake_floor, "quarantined": blocked, "gate_cases": kept}


def ci_cost(n_cases: int, *, cost_per_case: float, repeats: int = 1, judge_share: float = 0.0) -> dict[str, Any]:
    base = n_cases * cost_per_case * repeats
    judge = base * judge_share
    return {
        "n_cases": n_cases,
        "repeats": repeats,
        "deterministic_usd": round(base - judge, 4),
        "judge_usd": round(judge, 4),
        "total_usd": round(base, 4),
    }


def gate_ladder_decision(
    *,
    deterministic_pass: bool,
    fast_pass: bool,
    slow_pass: bool,
    flake_blocked: bool,
) -> dict[str, Any]:
    """Signature 9 decision path for a PR."""
    if not deterministic_pass:
        step, decision = "deterministic", "BLOCK"
    elif flake_blocked:
        step, decision = "fast_suite", "BLOCK_FLAKE"
    elif not fast_pass:
        step, decision = "fast_suite", "BLOCK"
    elif not slow_pass:
        step, decision = "slow_suite", "BLOCK"
    else:
        step, decision = "canary", "PROMOTE"
    return {
        "signature": 9,
        "ladder": list(LADDER_STEPS),
        "failed_at": step if decision != "PROMOTE" else None,
        "next_step": step,
        "decision": decision,
    }


def workflow_record(pr_id: str, decision: str, digest: str) -> dict[str, Any]:
    return {
        "pr_id": pr_id,
        "decision": decision,
        "suite_digest": digest,
        "runner": "github_actions",
        "truss": "v5",
    }


def pair_failures_to_main(
    pr_rows: Sequence[Mapping[str, Any]],
    main_rows: Sequence[Mapping[str, Any]],
    *,
    id_key: str = "id",
    ok_key: str = "ok",
) -> dict[str, Any]:
    """Provenance pairing: attribute PR fails relative to main on stable case ids.

    Categories: pr_only_fail (new regression owned by PR), both_fail (broken
    window), main_only_fail (unrelated to PR scorecard), both_pass.
    Fixture status labelled by caller (SIMULATED teaching suites).
    """
    main = {str(r[id_key]): bool(r.get(ok_key, True)) for r in main_rows}
    pr = {str(r[id_key]): bool(r.get(ok_key, True)) for r in pr_rows}
    ids = sorted(set(main) | set(pr))
    pr_only, both_fail, main_only, both_pass, missing = [], [], [], [], []
    for i in ids:
        if i not in main or i not in pr:
            missing.append(i)
            continue
        mo, po = main[i], pr[i]
        if po and mo:
            both_pass.append(i)
        elif (not po) and mo:
            pr_only.append(i)
        elif (not po) and (not mo):
            both_fail.append(i)
        else:
            main_only.append(i)
    return {
        "n_ids": len(ids),
        "pr_only_fail": pr_only,
        "both_fail": both_fail,
        "main_only_fail": main_only,
        "both_pass": both_pass,
        "missing_on_one_side": missing,
        "new_regression_count": len(pr_only),
        "broken_window_count": len(both_fail),
        "method": "provenance_pair_to_main",
        "fixture_status": "SIMULATED",
    }


def quarantine_decision(
    case_id: str,
    repeats: Sequence[bool],
    *,
    flake_floor: float = 0.10,
    min_flips: int = 2,
) -> dict[str, Any]:
    """Decide quarantine vs hard-fail for one case from repeat outcomes.

    True in repeats means pass. Quarantine when fail_rate > floor AND flips
    >= min_flips AND the case ever passed (not a stable wrong).
    """
    fr = flake_rate(repeats)
    stable_wrong = (not any(repeats))  # never passed
    q = bool(fr["quarantine"] and fr["flip_transitions"] >= min_flips and not stable_wrong)
    # flake_rate already uses rate>0.10; honour explicit floor
    if fr["fail_rate"] <= flake_floor:
        q = False
    action = "QUARANTINE" if q else ("HARD_FAIL" if fr["fail_rate"] > 0 else "PASS")
    if stable_wrong and fr["fail_rate"] > flake_floor:
        action = "HARD_FAIL_STABLE"
    return {
        "case_id": case_id,
        "fail_rate": fr["fail_rate"],
        "flip_transitions": fr["flip_transitions"],
        "flake_floor": flake_floor,
        "min_flips": min_flips,
        "quarantine": q,
        "action": action,
        "n": fr["n"],
        "fixture_status": "SIMULATED",
    }


def debug_slow_regression(
    suite: Mapping[str, Any],
    *,
    paired: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarise a slow-suite BLOCK for authors: det fails vs judge fails vs flake.

    Expects run_suite-style rows under suite['rows']. Optional paired provenance
    summary from pair_failures_to_main.
    """
    rows = list(suite.get("rows") or [])
    det_fails = [r["id"] for r in rows if r.get("det") and not r["det"].get("pass")]
    judge_fails = [
        r["id"] for r in rows
        if r.get("det") and r["det"].get("pass") and not r.get("ok")
    ]
    flake_ids = [r["id"] for r in rows if r.get("flake")]
    out = {
        "mode": suite.get("mode"),
        "n": suite.get("n"),
        "n_pass": suite.get("n_pass"),
        "pass_rate": suite.get("pass_rate"),
        "deterministic_fail_ids": det_fails,
        "judge_fail_ids": judge_fails,
        "flake_flagged_ids": flake_ids,
        "n_det_fail": len(det_fails),
        "n_judge_fail": len(judge_fails),
        "fixture_status": "SIMULATED",
    }
    if paired is not None:
        out["provenance"] = {
            "new_regression_count": paired.get("new_regression_count"),
            "broken_window_count": paired.get("broken_window_count"),
            "pr_only_fail": paired.get("pr_only_fail"),
        }
    return out
