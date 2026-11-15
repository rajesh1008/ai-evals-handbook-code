"""Truss shadow: dry-run tool policy, agreement reports, exit rules, disagreement samples (v6.5)."""
from __future__ import annotations
from typing import Any, Sequence
import hashlib

def dry_run_allowed(tool_name: str, dry_run_allowlist: Sequence[str]) -> bool:
    return tool_name in set(dry_run_allowlist)

def shadow_tool_call(tool_name: str, dry_run_allowlist: Sequence[str], execute: bool = False) -> dict[str, Any]:
    allowed = dry_run_allowed(tool_name, dry_run_allowlist)
    if not allowed and execute:
        return {"ok": False, "side_effect": True, "blocked": False, "tool": tool_name, "error": "tool_not_in_dry_run"}
    if not allowed:
        return {"ok": False, "side_effect": False, "blocked": True, "tool": tool_name, "error": "tool_not_in_dry_run"}
    return {"ok": True, "side_effect": False, "blocked": False, "tool": tool_name, "mode": "dry_run"}

def agreement_report(rows: Sequence[dict[str, Any]], slice_key: str = "flow") -> dict[str, Any]:
    n = len(rows)
    n_agree = sum(1 for r in rows if r.get("agree"))
    overall = n_agree / n if n else 0.0
    slices: dict[str, dict[str, Any]] = {}
    for r in rows:
        k = r.get(slice_key, "unknown")
        s = slices.setdefault(k, {"n": 0, "n_agree": 0})
        s["n"] += 1
        s["n_agree"] += int(bool(r.get("agree")))
    for k, s in slices.items():
        s["rate"] = s["n_agree"] / s["n"] if s["n"] else 0.0
    return {"n": n, "n_agree": n_agree, "n_disagree": n - n_agree, "overall": overall, "by_slice": slices}

def exit_rule_eval(overall: float, slice_rates: dict[str, float], floors: dict[str, float]) -> dict[str, Any]:
    checks = {"overall": overall >= floors.get("overall", 1.0)}
    for name, floor in floors.items():
        if name == "overall":
            continue
        checks[name] = slice_rates.get(name, 0.0) >= floor
    met = all(checks.values())
    return {"met": met, "checks": checks, "floors": floors, "decision": "PROMOTE" if met else "HOLD"}

def disagreement_sample(rows: Sequence[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    out = [r for r in rows if not r.get("agree")]
    return out[:limit]

def shadow_run_record(run_id: str, candidate_pin: str, n: int, dry_run_allowlist: Sequence[str], exit_floors: dict[str, float]) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "candidate_pin": candidate_pin,
        "n": n,
        "dry_run_allowlist": list(dry_run_allowlist),
        "exit_floors": exit_floors,
        "customer_visible": False,
    }

def digest_rows(rows: Sequence[dict[str, Any]]) -> str:
    payload = [(r.get("id"), r.get("flow"), int(bool(r.get("agree")))) for r in rows]
    return hashlib.sha256(repr(payload).encode()).hexdigest()[:12]
