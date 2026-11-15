"""Change-survival evaluation helpers (Chapter 29).

Paired upgrade deltas, slice regression tables, silent tool-schema catches,
text-versus-tool gates, upgrade experiment records, ownership registers and
eval-set rot scans. Numbers in chapter labs are SIMULATED fixtures unless a
REAL Anthropic run file says otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable, Mapping, Sequence


def paired_case_delta(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    case_id_key: str = "case_id",
    pass_key: str = "pass",
) -> dict[str, Any]:
    """Compare two runs case-by-case.

    A regression is pass under baseline and fail under candidate.
    An improvement is fail under baseline and pass under candidate.
    """
    b = {row[case_id_key]: bool(row[pass_key]) for row in baseline}
    c = {row[case_id_key]: bool(row[pass_key]) for row in candidate}
    ids = sorted(set(b) & set(c))
    regress = [i for i in ids if b[i] and not c[i]]
    improve = [i for i in ids if (not b[i]) and c[i]]
    both_pass = [i for i in ids if b[i] and c[i]]
    both_fail = [i for i in ids if (not b[i]) and (not c[i])]
    return {
        "n_paired": len(ids),
        "n_regress": len(regress),
        "n_improve": len(improve),
        "n_both_pass": len(both_pass),
        "n_both_fail": len(both_fail),
        "regress_ids": regress,
        "improve_ids": improve,
        "baseline_pass_rate": (sum(b[i] for i in ids) / len(ids)) if ids else 0.0,
        "candidate_pass_rate": (sum(c[i] for i in ids) / len(ids)) if ids else 0.0,
    }


def slice_regression_table(
    rows: Sequence[Mapping[str, Any]],
    *,
    slice_key: str = "slice",
    regress_key: str = "regressed",
) -> list[dict[str, Any]]:
    """Per-slice counts for change-aware regression reporting (CASPER-style)."""
    buckets: dict[str, list[bool]] = {}
    for row in rows:
        buckets.setdefault(str(row[slice_key]), []).append(bool(row[regress_key]))
    out = []
    for name in sorted(buckets):
        flags = buckets[name]
        n = len(flags)
        r = sum(flags)
        out.append({"slice": name, "n": n, "n_regress": r, "regress_rate": (r / n) if n else 0.0})
    return out


def schema_diff_catch(
    expected_schema: Mapping[str, Sequence[str]],
    observed_calls: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Catch silent tool-schema changes that text metrics miss.

    expected_schema maps tool name -> required argument names.
    observed_calls are {tool, args: dict, case_id?}.
    A call fails when the tool is unknown or a required arg is missing.
    """
    fails = []
    passes = 0
    for call in observed_calls:
        tool = call.get("tool")
        args = call.get("args") or {}
        case_id = call.get("case_id")
        if tool not in expected_schema:
            fails.append({"case_id": case_id, "tool": tool, "reason": "unknown_tool"})
            continue
        missing = [a for a in expected_schema[tool] if a not in args]
        if missing:
            fails.append({"case_id": case_id, "tool": tool, "reason": "missing_args", "missing": missing})
        else:
            passes += 1
    n = passes + len(fails)
    return {
        "n_calls": n,
        "n_pass": passes,
        "n_fail": len(fails),
        "pass_rate": (passes / n) if n else 0.0,
        "fails": fails,
    }


def text_vs_tool_gate(
    text_pass: bool,
    tool_pass: bool,
) -> dict[str, Any]:
    """Gate that refuses to ship on text-only greens when tools fail."""
    ship = bool(text_pass and tool_pass)
    kind = (
        "both_green" if text_pass and tool_pass else
        "text_green_tool_red" if text_pass and not tool_pass else
        "text_red_tool_green" if (not text_pass) and tool_pass else
        "both_red"
    )
    return {"text_pass": text_pass, "tool_pass": tool_pass, "ship": ship, "kind": kind}


@dataclass(frozen=True)
class UpgradeExperiment:
    name: str
    baseline_pin: str
    candidate_pin: str
    suite_digest: str
    n_cases: int
    text_delta: float
    tool_delta: float
    decision: str  # ship | hold | canary | rollback
    owner: str
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def upgrade_experiment_record(**kwargs: Any) -> dict[str, Any]:
    """Treat a model upgrade as a named experiment with an explicit decision."""
    exp = UpgradeExperiment(**kwargs)
    if exp.decision not in {"ship", "hold", "canary", "rollback"}:
        raise ValueError(f"unknown decision: {exp.decision}")
    if exp.n_cases < 1:
        raise ValueError("n_cases must be positive")
    return exp.as_dict()


def ownership_register(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalise eval-data ownership rows: artefact, owner, backup, review_cadence."""
    required = {"artefact", "owner", "backup", "review_cadence"}
    out = []
    for row in rows:
        missing = required - set(row)
        if missing:
            raise ValueError(f"ownership row missing {sorted(missing)}")
        out.append({k: row[k] for k in ("artefact", "owner", "backup", "review_cadence", "notes") if k in row or k != "notes"})
        if "notes" in row:
            out[-1]["notes"] = row["notes"]
    return out


def rot_staleness_scan(
    cases: Sequence[Mapping[str, Any]],
    *,
    current_policy_version: str,
    policy_key: str = "policy_version",
    stale_key: str = "gold_matches_current",
) -> dict[str, Any]:
    """Scan an eval set for rot after prompt or policy changes."""
    stale = []
    fresh = []
    for case in cases:
        cid = case.get("case_id")
        matches = case.get(stale_key)
        if matches is None:
            matches = case.get(policy_key) == current_policy_version
        if matches:
            fresh.append(cid)
        else:
            stale.append(cid)
    n = len(fresh) + len(stale)
    return {
        "current_policy_version": current_policy_version,
        "n": n,
        "n_fresh": len(fresh),
        "n_stale": len(stale),
        "stale_rate": (len(stale) / n) if n else 0.0,
        "stale_ids": stale,
    }
