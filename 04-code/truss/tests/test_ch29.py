from truss.change import (
    paired_case_delta, slice_regression_table, schema_diff_catch,
    text_vs_tool_gate, upgrade_experiment_record, ownership_register, rot_staleness_scan,
)
from truss import __version__

def test_version():
    assert int(__version__.split(".")[1]) >= 32

def test_paired_and_slices():
    b = [{"case_id": "a", "pass": True}, {"case_id": "b", "pass": True}]
    c = [{"case_id": "a", "pass": False}, {"case_id": "b", "pass": True}]
    d = paired_case_delta(b, c)
    assert d["n_regress"] == 1 and d["regress_ids"] == ["a"]
    rows = [{"slice": "fee", "regressed": True}, {"slice": "fee", "regressed": False}, {"slice": "lien", "regressed": False}]
    t = slice_regression_table(rows)
    assert t[0]["slice"] == "fee" and t[0]["n_regress"] == 1

def test_schema_and_gate():
    schema = {"explain_fee": ["loan_id", "fee_code"]}
    calls = [{"case_id": "1", "tool": "explain_fee", "args": {"loan_id": "L1", "fee_code": "X"}},
             {"case_id": "2", "tool": "explain_fee", "args": {"account_id": "A1", "fee_code": "X"}}]
    r = schema_diff_catch(schema, calls)
    assert r["n_fail"] == 1 and r["n_pass"] == 1
    g = text_vs_tool_gate(True, False)
    assert g["kind"] == "text_green_tool_red" and not g["ship"]

def test_upgrade_and_ownership_and_rot():
    e = upgrade_experiment_record(
        name="x", baseline_pin="a", candidate_pin="b", suite_digest="abc",
        n_cases=10, text_delta=0.01, tool_delta=-0.05, decision="hold",
        owner="Ryan Mitchell", rationale="tool regress",
    )
    assert e["decision"] == "hold"
    own = ownership_register([{"artefact": "suite", "owner": "A", "backup": "B", "review_cadence": "weekly"}])
    assert own[0]["owner"] == "A"
    rot = rot_staleness_scan(
        [{"case_id": "1", "gold_matches_current": False}, {"case_id": "2", "gold_matches_current": True}],
        current_policy_version="p3",
    )
    assert rot["n_stale"] == 1

def test_lab_outputs():
    import json
    from pathlib import Path
    lab = Path(__file__).resolve().parents[2] / "ch29" / "out" / "lab.json"
    inj = Path(__file__).resolve().parents[2] / "ch29" / "out" / "inject.json"
    if not lab.exists():
        return
    d = json.loads(lab.read_text())
    assert d["regression_caught"] == "t-320118"
    assert d["experiment"]["decision"] == "hold"
    if inj.exists():
        j = json.loads(inj.read_text())
        assert j["text_metrics_pass"] and not j["ships_with_tool_gate"]
