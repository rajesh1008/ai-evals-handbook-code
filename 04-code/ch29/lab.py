"""Run model-upgrade experiment through Truss change helpers."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.change import (
    paired_case_delta, slice_regression_table, schema_diff_catch,
    text_vs_tool_gate, upgrade_experiment_record, ownership_register, rot_staleness_scan,
)

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())

print("Chapter 29 lab: evals that survive change")
cases = FIX["cases"]
base_text = [{"case_id": c["case_id"], "pass": c["baseline"]["text_pass"]} for c in cases]
cand_text = [{"case_id": c["case_id"], "pass": c["candidate"]["text_pass"]} for c in cases]
base_tool = [{"case_id": c["case_id"], "pass": c["baseline"]["tool_pass"]} for c in cases]
cand_tool = [{"case_id": c["case_id"], "pass": c["candidate"]["tool_pass"]} for c in cases]

text_delta = paired_case_delta(base_text, cand_text)
tool_delta = paired_case_delta(base_tool, cand_tool)

regress_rows = []
for c in cases:
    regressed = c["baseline"]["tool_pass"] and (not c["candidate"]["tool_pass"])
    regress_rows.append({"slice": c["slice"], "regressed": regressed, "case_id": c["case_id"]})
slices = slice_regression_table(regress_rows)

# Silent schema: agents still send loan_id; v2 expects account_id on fee/get_loan
silent = schema_diff_catch(FIX["schema_v2_silent"], [c["tool_call"] for c in cases])
v1_ok = schema_diff_catch(FIX["schema_v1"], [c["tool_call"] for c in cases])

text_rate_b = text_delta["candidate_pass_rate"]
tool_rate_b = tool_delta["candidate_pass_rate"]
gate = text_vs_tool_gate(text_rate_b >= 0.90, tool_rate_b >= 0.90)

exp = upgrade_experiment_record(
    name="harbor-first-hardship-model-upgrade",
    baseline_pin=FIX["baseline_pin"],
    candidate_pin=FIX["candidate_pin"],
    suite_digest=FIX["digest"],
    n_cases=FIX["n"],
    text_delta=round(text_delta["candidate_pass_rate"] - text_delta["baseline_pass_rate"], 4),
    tool_delta=round(tool_delta["candidate_pass_rate"] - tool_delta["baseline_pass_rate"], 4),
    decision="hold" if not gate["ship"] else "ship",
    owner="Ryan Mitchell",
    rationale="Text improved; tool regressions on fee/hardship; silent schema catch on loan_id→account_id.",
)

owners = ownership_register([
    {"artefact": "hardship regression suite", "owner": "Ryan Mitchell", "backup": "Sarah Lindqvist", "review_cadence": "every prompt change"},
    {"artefact": "tool schema pins", "owner": "Sarah Lindqvist", "backup": "Ryan Mitchell", "review_cadence": "every tool deploy"},
    {"artefact": "rate targets wrong-hardship / wrong-fee", "owner": "Victor Lane", "backup": "Rachel Foster", "review_cadence": "monthly"},
    {"artefact": "gold labels fee/hardship", "owner": "Diane Porter", "backup": "Ryan Mitchell", "review_cadence": "after policy edit"},
])

rot = rot_staleness_scan(cases, current_policy_version=FIX["current_policy_version"])

# Named plant must be in tool regressions
assert "t-320118" in tool_delta["regress_ids"]

out = {
    "kind": "SIMULATED",
    "digest": FIX["digest"],
    "text_delta": text_delta,
    "tool_delta": tool_delta,
    "slices": slices,
    "schema_v1": v1_ok,
    "schema_silent_v2": silent,
    "gate": gate,
    "experiment": exp,
    "ownership": owners,
    "rot": rot,
    "regression_caught": "t-320118",
    "n_tool_regress": tool_delta["n_regress"],
    "n_text_regress": text_delta["n_regress"],
}
(OUT / "lab.json").write_text(json.dumps(out, indent=2))
print(json.dumps({
    "text_base": round(text_delta["baseline_pass_rate"], 3),
    "text_cand": round(text_delta["candidate_pass_rate"], 3),
    "tool_base": round(tool_delta["baseline_pass_rate"], 3),
    "tool_cand": round(tool_delta["candidate_pass_rate"], 3),
    "tool_regress": tool_delta["n_regress"],
    "silent_fail": silent["n_fail"],
    "stale": rot["n_stale"],
    "decision": exp["decision"],
    "plant": "t-320118",
}, indent=2))
