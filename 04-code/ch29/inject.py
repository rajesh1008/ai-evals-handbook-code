"""Failure injection: silent tool-schema change that passes every text metric."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.change import schema_diff_catch, text_vs_tool_gate, paired_case_delta

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
cases = FIX["cases"]

# Under injection, keep baseline text scores; only schema changes
text_rows = [{"case_id": c["case_id"], "pass": c["baseline"]["text_pass"]} for c in cases]
# Fake "after" text still identical
text_after = list(text_rows)
text_cmp = paired_case_delta(text_rows, text_after)

silent = schema_diff_catch(FIX["schema_v2_silent"], [c["tool_call"] for c in cases])
honest = schema_diff_catch(FIX["schema_v1"], [c["tool_call"] for c in cases])

# Text metrics: all green relative to themselves; tool gate red
text_all_green = text_cmp["n_regress"] == 0 and text_cmp["candidate_pass_rate"] >= 0.90
tool_green = silent["pass_rate"] >= 0.90
gate = text_vs_tool_gate(text_all_green, tool_green)

out = {
    "kind": "SIMULATED_INJECTION",
    "name": "silent_loan_id_to_account_id",
    "text_metrics_pass": text_all_green,
    "text_pass_rate": text_cmp["candidate_pass_rate"],
    "text_regressions": text_cmp["n_regress"],
    "schema_v1_pass_rate": honest["pass_rate"],
    "schema_silent_pass_rate": silent["pass_rate"],
    "schema_silent_n_fail": silent["n_fail"],
    "gate": gate,
    "caught_by": "schema_diff_catch + text_vs_tool_gate",
    "would_ship_on_text_only": text_all_green,
    "ships_with_tool_gate": gate["ship"],
}
(OUT / "inject.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
assert out["text_metrics_pass"] and not out["ships_with_tool_gate"]
print("injection OK: text green, tool gate holds")
