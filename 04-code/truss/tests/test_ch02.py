"""Chapter 2: rates, completeness, labeller and gate."""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ch02"))
from truss.complete import completeness  # noqa: E402
from truss.gate import decide  # noqa: E402
from truss.label import session  # noqa: E402
from truss.rates import traces_needed, upper_bound, weighted_rate, wilson  # noqa: E402


def test_zero_in_100_bound_and_598():
    assert round(upper_bound(0, 100), 3) == 0.030
    assert traces_needed(0.005) == 598
    assert traces_needed(0.005, failures=1) == 947
    assert round(upper_bound(0, 40), 3) == 0.072


def test_wilson_91_percent():
    lo, hi = wilson(273, 300)
    assert 0.872 < lo < 0.873 and 0.937 < hi < 0.938


def test_weighting():
    assert weighted_rate({"a": (9, 10), "b": (5, 10)}, {"a": 0.75, "b": 0.25}) == 0.8


def test_completeness_flags_missing_lookup():
    ok, bad = completeness([{"trace_id": "x", "flow": "fee_explanation", "tools": ["get_account"]}])
    assert not ok and bad[0]["missing"] == ["get_fee_schedule"]


def test_label_session_resumes(tmp_path):
    t = {"trace_id": "t1", "flow": "hardship", "turns": 3, "tools": [], "messages": []}
    u = {**t, "trace_id": "t2"}
    path = tmp_path / "labels.csv"
    session([t], path, "Grace", iter(["f offer before income"]), io.StringIO())
    assert session([t, u], path, "Grace", iter(["p"]), io.StringIO()) == 1
    assert path.read_text().count("\n") == 3


def test_fail_needs_note():
    t = {"trace_id": "t1", "flow": "hardship", "turns": 3, "tools": [], "messages": []}
    try:
        session([t], "/dev/null", "Grace", iter(["f"]), io.StringIO())
    except ValueError:
        return
    raise AssertionError("a fail without a note was accepted")


def test_gate_holds_on_new_hardship_failure():
    v, reasons = decide(True, 0, {"hardship": (1, 0), "account_question": (0, 3)}, 0)
    assert v == "hold" and "hardship" in reasons[0]
    assert decide(True, 0, {"account_question": (0, 3)}, 0)[0] == "ship"


def test_lab_numbers():
    from pilot_detail import first_pass_labels
    labels = first_pass_labels()
    assert sum(r["verdict"] == "pass" for r in labels) == 273
    assert not any("outside policy" in r["note"] for r in labels)
