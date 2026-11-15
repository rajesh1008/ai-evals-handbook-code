"""Incident to eval: the post-mortem loop (Chapter 39).

Turn complaints and incidents into regression cases, track time-to-eval,
distinguish symptom tests from failure-mode tests, and replay cases across
releases.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping, Sequence


def parse_day(s: str) -> date:
    return date.fromisoformat(s)


def time_to_eval_days(incident_opened: str, eval_merged: str) -> int:
    a, b = parse_day(incident_opened), parse_day(eval_merged)
    return (b - a).days


def incident_record(
    incident_id: str,
    *,
    opened: str,
    symptom: str,
    failure_mode: str,
    owner: str,
) -> dict[str, Any]:
    return {
        "incident_id": incident_id,
        "opened": opened,
        "symptom": symptom,
        "failure_mode": failure_mode,
        "owner": owner,
    }


def regression_case(
    case_id: str,
    *,
    incident_id: str,
    failure_mode: str,
    against: str,
    owner: str,
    neighbour_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    if against not in ("failure_mode", "symptom"):
        raise ValueError("against must be failure_mode or symptom")
    return {
        "case_id": case_id,
        "incident_id": incident_id,
        "failure_mode": failure_mode,
        "against": against,
        "owner": owner,
        "neighbour_ids": list(neighbour_ids or ()),
        "is_symptom_test": against == "symptom",
    }


def symptom_vs_failure_mode(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "against": case["against"],
        "is_symptom_test": bool(case.get("is_symptom_test")),
        "usable_as_gate": case.get("against") == "failure_mode",
        "label": "SYMPTOM_TEST" if case.get("against") == "symptom" else "FAILURE_MODE_TEST",
    }


def replay_on_releases(
    case: Mapping[str, Any],
    releases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """releases: [{name, fails_modes: set/list of failure_mode strings that still fail}]"""
    fm = case["failure_mode"]
    rows = []
    for r in releases:
        fails = set(r.get("fails_modes", []))
        # symptom tests may pass even when FM still present
        if case.get("against") == "symptom":
            still_fails = bool(r.get("symptom_still_visible", False))
        else:
            still_fails = fm in fails
        rows.append({"release": r["name"], "fails": still_fails})
    n_fail = sum(1 for x in rows if x["fails"])
    return {
        "case_id": case["case_id"],
        "against": case["against"],
        "n_releases": len(rows),
        "n_fail": n_fail,
        "rows": rows,
        "caught_on_latest": bool(rows[-1]["fails"]) if rows else False,
    }


def complaint_neighbours(
    seed_trace: str,
    *,
    n: int,
    stratum: str,
) -> dict[str, Any]:
    ids = [f"{seed_trace}-n{i:02d}" for i in range(1, n + 1)]
    return {"seed_trace": seed_trace, "stratum": stratum, "n": n, "neighbour_ids": ids}


def weekly_report(
    *,
    median_tte_days: float,
    n_incidents_closed_to_eval: int,
    n_symptom_rejected: int,
    complaints_this_month: int,
    complaints_prev_month: int,
) -> dict[str, Any]:
    return {
        "median_tte_days": median_tte_days,
        "n_incidents_closed_to_eval": n_incidents_closed_to_eval,
        "n_symptom_rejected": n_symptom_rejected,
        "complaints_this_month": complaints_this_month,
        "complaints_prev_month": complaints_prev_month,
        "complaints_falling": complaints_this_month < complaints_prev_month,
    }


def taxonomy_change_from_review(
    review_id: str,
    *,
    new_failure_mode: str,
    action: str,
) -> dict[str, Any]:
    if action not in ("add", "split", "retire"):
        raise ValueError("action must be add, split or retire")
    return {
        "review_id": review_id,
        "new_failure_mode": new_failure_mode,
        "action": action,
        "produces_fix": True,
    }
