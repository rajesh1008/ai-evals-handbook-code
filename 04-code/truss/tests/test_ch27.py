from truss.authority import permission_trace, forbidden_path_pass, refusal_quality, escalation_correct, aggregate_authority, adversarial_suite_summary, HARDSHIP_FORBIDDEN
from truss import __version__

def test_version():
    assert int(__version__.split(".")[1]) >= 30

def test_permission_and_forbidden():
    steps = [{"tool": "get_loan"}, {"tool": "wire_funds"}]
    pt = permission_trace(steps)
    assert pt["n_forbidden"] == 1 and not pt["authority_ok"]
    fp = forbidden_path_pass(True, False)
    assert fp["forbidden_path_pass"]

def test_refusal_escalation():
    assert refusal_quality(True, True, True)["kind"] == "correct_refusal"
    assert refusal_quality(True, False, False)["kind"] == "over_refusal"
    assert escalation_correct(True, True)["ok"]

def test_aggregate_and_adv():
    a = aggregate_authority([{"authority_ok": True, "forbidden_path_pass": False}, {"authority_ok": False, "forbidden_path_pass": True}])
    assert a["n"] == 2 and a["forbidden_path_passes"] == 1
    s = adversarial_suite_summary([{"family": "x", "caught": True}, {"family": "x", "caught": False}])
    assert s["catch_rate"] == 0.5

def test_forbidden_set():
    assert "wire_funds" in HARDSHIP_FORBIDDEN

def test_fixture():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "ch27" / "out" / "fixture.json"
    if not p.exists():
        return
    d = json.loads(p.read_text())
    assert d["n"] == 500 and d["kind_counts"]["forbidden_path"] == 40

def test_lab_touchpoint():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "ch27" / "out" / "lab.json"
    if not p.exists():
        return
    d = json.loads(p.read_text())
    assert d["authority"]["forbidden_path_passes"] == 40
