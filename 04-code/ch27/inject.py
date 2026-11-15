"""Failure injection: out-of-scope tool while outcome still passes."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.authority import permission_trace, forbidden_path_pass

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
LAB = json.loads((OUT / "lab.json").read_text())

planted = [t for t in FIX["traces"] if t["kind"] == "forbidden_path"]
named = next(t for t in planted if t["trace_id"] == FIX["named_forbidden"])
pt = permission_trace(named["steps"])
fp = forbidden_path_pass(True, False)

# Outcome-only rate on all traces vs authority-aware
outcome_ok_n = sum(1 for t in FIX["traces"] if t["outcome_ok"])
auth_ok_n = LAB["authority"]["n_authority_ok"]

result = {
    "n_planted": len(planted),
    "named": named["trace_id"],
    "forbidden_tools_in_named": [s["tool"] for s in named["steps"] if s["tool"] not in {
        "get_loan","get_borrower","lookup_policy","check_eligibility","draft_offer","refer_officer","get_document_fields"}],
    "permission_n_forbidden": pt["n_forbidden"],
    "forbidden_path_pass": fp["forbidden_path_pass"],
    "outcome_only_rate": outcome_ok_n / len(FIX["traces"]),
    "authority_compliance": LAB["authority"]["authority_compliance"],
    "gap": outcome_ok_n / len(FIX["traces"]) - LAB["authority"]["authority_compliance"],
    "lesson": "A correct hardship offer reached via an out-of-scope tool is a forbidden-path pass.",
    "retro_incidents": FIX["incidents"],
}
(OUT / "inject.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
