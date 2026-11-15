from datetime import date

from truss.checks import within_months
from truss.flowsuite import (Row, decision_table, composition_audit, newly_failing, two_way_gate, reachable,
                             refine, weeks_to, traces_needed)


def test_decision_table_drops_rows_without_threshold_owner_or_action():
    rows = [Row("MC-01", "wrong offer?", "any stable new failure", "Grace", "hold the release", "gate"),
            Row("accuracy", "right first action?"),
            Row("offer rate", "share offered", owner="Rachel"),
            Row("S-02", "self-serve rate", owner="Rachel", tier="inform"), Row("S-01", "CSAT", tier="inform")]
    t = decision_table(rows)
    assert [r.metric for r in t["kept"]] == ["MC-01", "S-02"] and [r.metric for r in t["gates"]] == ["MC-01"]
    why = {r.metric: w for r, w in t["dropped"]}
    assert why["accuracy"] == "no threshold, no owner, no action"
    assert why["offer rate"] == "no threshold, no action" and why["S-01"] == "no owner"


def test_composition_audit_flags_thin_and_missing_segments():
    frame = [{"s": "a"}] * 80 + [{"s": "b"}] * 20
    good = [{"s": "a"}] * 60 + [{"s": "b"}] * 20
    assert composition_audit(good, frame, lambda c: c["s"])["verdict"] == "accept"
    thin = [{"s": "a"}] * 95 + [{"s": "b"}] * 5
    a = composition_audit(thin, frame, lambda c: c["s"])
    assert a["verdict"] == "refuse" and a["failing"] == ["b"]
    gone = composition_audit([{"s": "a"}] * 100, frame, lambda c: c["s"])
    assert gone["segments"]["b"]["gate_n"] == 0 and not gone["segments"]["b"]["pass"]


def test_composition_audit_counts_overlapping_flags():
    frame = [{"f": ["x", "y"]}] * 30
    a = composition_audit(frame, frame, lambda c: c["f"])
    assert a["segments"]["x"]["gate_n"] == 30 and a["segments"]["y"]["gate_n"] == 30


def test_newly_failing_needs_every_rerun():
    base = [{"1": False, "2": False, "3": True}, {"1": False, "2": False, "3": False}]
    cand = [{"1": True, "2": True, "3": True}, {"1": True, "2": False, "3": True}]
    r = newly_failing(base, cand)
    assert r["new"] == ["1"] and r["single_run"] == ["2"] and r["production_flips"] == ["3"]


def test_two_way_gate_holds_on_either_direction_while_accuracy_rises():
    req = {"a": "draft_deferral", "b": "draft_deferral", "c": "decline_window", "d": "decline_window"}
    base = [{"a": "decline_window", "b": "decline_window", "c": "decline_window", "d": "decline_window"}] * 2
    cand = [{"a": "draft_deferral", "b": "draft_deferral", "c": "draft_deferral", "d": "decline_window"}] * 2
    g = two_way_gate(req, base, cand)
    assert g["accuracy"]["cand"] > g["accuracy"]["base"]
    assert g["verdict"] == "hold" and g["holds_on"] == ["offer"] and g["offer"]["new"] == ["c"]
    assert g["refusal"]["n"] == 2 and g["refusal"]["new"] == []


def test_reachability_and_sample_sizes():
    r = reachable(7, 657, 0.005)
    assert not r["reachable_by_sampling"] and not r["shown"] and 0.019 < r["upper"] < 0.020
    assert reachable(0, 700, 0.005)["shown"]
    assert [traces_needed(0.005, k) for k in range(4)] == [598, 947, 1258, 1549]
    assert refine(0.001, 0.005) == 947 and refine(0.0107, 0.005) is None
    assert weeks_to(947, 657, 60) == (947 - 657) / 60 and weeks_to(500, 657, 60) == 0.0


def test_within_months_anniversary_readings():
    end, today = date(2026, 9, 14), date(2027, 9, 14)
    assert within_months(end, today) is True
    assert within_months(end, today, anniversary_inside=False) is False
    assert within_months(date(2026, 9, 15), today, anniversary_inside=False) is True
