"""Failure injection: an agent that reaches the right offer by calling the wrong tool
with a guessed argument (compute_plan). Compares outcome-only vs process scoring."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.trajectory import score_trajectory, lucky_pass

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
lucky = [t for t in FIX["trajectories"] if t["kind"] == "lucky"]
print(f"Injection set: {len(lucky)} lucky-pass trajectories")
outcome_pass = sum(1 for t in lucky if t["outcome_ok"])
checklist = [
    {"id": "loan", "tool": "get_loan", "required_args": ["loan_id"]},
    {"id": "borrower", "tool": "get_borrower", "required_args": ["borrower_id"]},
    {"id": "policy", "tool": "lookup_policy", "required_args": ["topic"]},
    {"id": "elig", "tool": "check_eligibility", "required_args": ["loan_id", "reason"]},
]
process_pass = 0
for t in lucky:
    sc = score_trajectory(t["steps"], checklist=checklist)
    if sc["exact_match"]:
        process_pass += 1
    lp = lucky_pass(t["outcome_ok"], t["process_ok"])
    assert lp["is_lucky_pass"], t["trace_id"]
named = next(t for t in lucky if t["trace_id"] == "t-270087")
print(f"outcome-only pass: {outcome_pass}/{len(lucky)}")
print(f"checklist process pass: {process_pass}/{len(lucky)}")
print(f"named t-270087 tools: {[s['tool'] for s in named['steps']]}")
print(f"named args on compute_plan: {named['steps'][2]['args']}")
result = {
    "n": len(lucky),
    "outcome_pass": outcome_pass,
    "process_pass": process_pass,
    "named": "t-270087",
    "named_tools": [s["tool"] for s in named["steps"]],
}
(OUT / "inject.json").write_text(json.dumps(result, indent=2))
print("wrote out/inject.json")
