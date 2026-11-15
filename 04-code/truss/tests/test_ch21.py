"""Tests for truss.trial (Chapter 21). Seven tests, matching prior chapters."""
import math
from truss.trial import (validation_table, disagreement_causes, construct_profile, surface_agreement,
                         escape_bound, seen_through, admit_part, split_verdict, decision_record)


def _expand(tp, fn, fp, tn, pos="fail", neg="pass"):
    truth = [pos] * tp + [pos] * fn + [neg] * fp + [neg] * tn
    pred = [pos] * tp + [neg] * fn + [pos] * fp + [neg] * tn
    return truth, pred


def test_validation_table_counts_abstentions_as_misses():
    truth, pred = _expand(29, 18, 11, 140)
    truth += ["fail", "pass"]
    pred += ["cannot_tell", "cannot_tell"]
    t = validation_table(truth, pred, ["k"] * len(truth))
    assert (t["tp"], t["fn"], t["fp"], t["tn"], t["P"], t["N"]) == (29, 18, 11, 140, 48, 152)
    assert t["agree_n"] == 169 and abs(t["tpr"] - 29 / 48) < 1e-12
    assert round(t["tpr_ci"][0], 3) == 0.463 and round(t["tnr_ci"][0], 3) == 0.867


def test_by_kind_and_segment_rows():
    t = validation_table(["fail", "fail", "pass", "pass"], ["fail", "pass", "pass", "fail"],
                         ["window", "window", "ordinary", "ordinary"], ["en", "es", "en", "es"])
    assert t["by_kind"]["window"] == {"n": 2, "gold_fail": 2, "right": 1, "abstain": 0}
    assert t["by_segment"]["es"]["tp"] == 0 and t["by_segment"]["es"]["tnr"] == 0.0


def test_disagreement_causes_mechanical_share():
    rows = [{"cause": c} for c in ["date_arithmetic"] * 12 + ["stated_vs_record"] * 10 + ["income_arithmetic"] * 3
            + ["policy_rule"] * 3 + ["other"] * 3]
    d = disagreement_causes(rows)
    assert d["n"] == 31 and d["mechanical"] == 15 and abs(d["mechanical_share"] - 15 / 31) < 1e-12
    assert list(d["by_cause"])[0] == "date_arithmetic"


def test_construct_profile_separates_stability_from_sensitivity():
    base = ["pass"] * 40
    preserved = ["pass"] * 38 + ["fail"] * 2
    changed = ["fail"] * 15 + ["pass"] * 25
    p = construct_profile(base, preserved, changed, ["date"] * 10 + ["stated"] * 10 + ["loan"] * 10 + ["arrears"] * 10)
    assert p["S"] == 0.95 and p["R"] == 0.375
    assert p["R_by_type"]["date"] == {"n": 10, "changed": 10}


def test_surface_agreement_gap():
    s = surface_agreement([True, True, False, False], ["fail", "fail", "pass", "pass"], ["fail", "pass", "pass", "fail"])
    assert s["judge"] == 1.0 and s["gold"] == 0.5 and s["gap"] == 0.5


def test_escape_bound_needs_598_offers_for_half_a_percent():
    e = escape_bound(0, 200)
    assert not e["can_gate"] and round(e["perfect_upper"], 4) == 0.0149
    assert e["offers_needed_at_zero"] == 598
    assert escape_bound(0, 598)["can_gate"]
    assert math.isclose(seen_through(0.008, 29 / 48), 0.008 * 29 / 48)


def test_split_refuses_gate_when_one_part_fails():
    a = admit_part("A", {"tpr_ci": (0.847, 0.995), "tnr_ci": (0.949, 0.994)}, role="order")
    b = admit_part("B", {"tpr_ci": (0.612, 0.851), "tnr_ci": (0.917, 0.982)}, role="decide")
    v = split_verdict([a, b])
    assert a["admit"] and not b["admit"] and not v["gate_allowed"] and v["failed_parts"] == ["B"]
    assert v["admitted"] == [("A", "order")]
    d = decision_record({"fix": {"held_out_clean": False, "admitted": True}, "abandon": {"replacement": []}})
    assert not d["fix"]["supported_today"] and not d["abandon"]["supported_today"]
