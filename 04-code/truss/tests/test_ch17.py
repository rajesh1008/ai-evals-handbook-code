from truss.bias import (
    position_calls, position_summary, mitigate_position, flip_summary,
    self_pref_summary, label_effect, rubric_anchor, segment_table,
    majority, pairwise_agree, correlated_errors, evaluate_tests, disqualify,
    grade, THRESHOLDS,
)


def test_position_summary_values_match_pair_outcome():
    first = ["A", "A", "B", "A", "tie"]
    swapped = ["B", "A", "A", "B", "tie"]
    calls = position_calls(first, swapped)
    assert calls == ["original", "position", "other", "original", "tie"]
    s = position_summary(calls)
    assert s["position"] == 1 and s["original"] == 2 and s["other"] == 1 and s["tie"] == 1
    assert s["position_rate"] == 0.2
    m = mitigate_position(first, swapped, gold=["A", "B", "B", "A", "tie"])
    assert m["kept"] == ["A", "B", "A", "tie"] and m["n"] == 4
    # scored: A==A, B==B, A==A; tie skipped -> 3/3
    assert m["accuracy"] == 1.0 and m["n_scored"] == 3


def test_verbosity_flip_tracks_direction():
    base = ["A", "A", "B", "B", "tie"]
    padded = ["A", "B", "B", "A", "A"]  # flips at 1 (to B), 3 (to A), 4 (to A)
    toward = ["B", "B", "B", "B", "B"]  # B was padded
    f = flip_summary(base, padded, toward=toward)
    assert f["flipped"] == 3 and f["flip_rate"] == 0.6
    assert f["toward"] == 1 and f["toward_rate"] == 1 / 3  # only idx 1 moved onto padded B


def test_self_pref_uses_only_matched_mixed_family_pairs():
    rows = [
        {"judge_family": "S", "gen_A": "S", "gen_B": "X", "pick": "A", "gold": "tie", "quality_matched": True},
        {"judge_family": "S", "gen_A": "S", "gen_B": "X", "pick": "B", "gold": "tie", "quality_matched": True},
        {"judge_family": "S", "gen_A": "S", "gen_B": "S", "pick": "A", "gold": "tie", "quality_matched": True},
        {"judge_family": "S", "gen_A": "S", "gen_B": "X", "pick": "A", "gold": "A", "quality_matched": False},
    ]
    s = self_pref_summary(rows)
    assert s["used"] == 2 and s["skipped_same_or_neither"] == 1
    assert s["own"] == 1 and s["other"] == 1 and s["self_pref"] == 0.0


def test_label_effect_and_rubric_anchor():
    blind = ["A", "A", "B", "B"]
    tagged = ["A", "B", "B", "A"]  # flips at 1 (to B) and 3 (to A)
    tags = [("self", "B"), ("self", "B"), ("other", "B"), ("other", "B")]
    e = label_effect(blind, tagged, tags)
    assert e["flipped"] == 2
    # idx 1: self on B, tagged B -> toward_self
    # idx 3: other on B, blind B, tagged A -> away_other
    assert e["toward_self"] == 1 and e["away_other"] == 1
    recs = [
        ("p1", ("pass", "fail", "cannot_tell"), "pass"),
        ("p1", ("fail", "cannot_tell", "pass"), "fail"),  # first slot both times
        ("p2", ("pass", "fail", "cannot_tell"), "fail"),
        ("p2", ("fail", "cannot_tell", "pass"), "fail"),  # content consistent
    ]
    a = rubric_anchor(recs)
    assert a["n"] == 4 and a["n_options"] == 3
    assert a["first"] == 3 and a["content_consistent"] == 1
    assert abs(a["excess_first"] - (0.75 - 1 / 3)) < 1e-9


def test_segment_gap_and_panel_correlation():
    rows = ([{"segment": "en", "success": True}] * 8
            + [{"segment": "en", "success": False}] * 2
            + [{"segment": "es", "success": True}] * 3
            + [{"segment": "es", "success": False}] * 7)
    t = segment_table(rows)
    assert t["en"]["rate"] == 0.8 and t["es"]["rate"] == 0.3
    assert abs(t["_max_gap"] - 0.5) < 1e-9
    gold = ["A", "A", "A", "B", "B", "B"]
    j1 =   ["A", "B", "A", "B", "A", "B"]  # wrong at 1, 4
    j2 =   ["A", "B", "B", "B", "A", "B"]  # wrong at 1, 2, 4
    c = correlated_errors(j1, j2, gold)
    assert c["a_wrong"] == 2 and c["b_wrong"] == 3 and c["both"] == 2 and c["either"] == 3
    assert c["both_given_either"] == 2 / 3
    assert c["majority"] if False else True
    assert majority([j1, j2, ["A", "A", "A", "B", "B", "B"]]) == ["A", "B", "A", "B", "A", "B"]
    ag = pairwise_agree(j1, j2)
    assert ag["agree"] == 5 and abs(ag["rate"] - 5 / 6) < 1e-9


def test_battery_flags_and_disqualify_rules():
    assert grade(0.04, 0.05, 0.10) == "pass"
    assert grade(0.09, 0.05, 0.10) == "flag"
    assert grade(0.10, 0.05, 0.10) == "fail"
    rows = evaluate_tests({"position_rate": 0.09, "verbosity_flip": 0.04,
                           "self_pref": 0.03, "authority_flip": 0.01})
    by = {r["name"]: r["verdict"] for r in rows}
    assert by["position_rate"] == "flag" and by["verbosity_flip"] == "pass"
    d = disqualify(rows, role="order")
    assert d["admit"] is True and d["flags"] == ["position_rate"] and d["fails"] == []
    # a fail on a role-critical test disqualifies
    rows2 = evaluate_tests({"position_rate": 0.12, "verbosity_flip": 0.04})
    d2 = disqualify(rows2, role="order")
    assert d2["admit"] is False and "position_rate" in d2["fails"]
    # two fails disqualify even if not critical for pointwise... authority and segment
    rows3 = evaluate_tests({"authority_flip": 0.09, "segment_gap": 0.25, "rubric_slot": 0.05})
    d3 = disqualify(rows3, role="pointwise")
    assert d3["admit"] is False and len(d3["fails"]) == 2
    d4 = disqualify(rows, role="decide")
    assert d4["admit"] is False and "Judge Report Card" in d4["reasons"][0]
    assert THRESHOLDS["position_rate"]["fail"] == 0.10


def test_position_interval_contains_the_rate():
    calls = ["original"] * 91 + ["position"] * 9
    s = position_summary(calls)
    assert s["position_rate"] == 0.09
    lo, hi = s["position_ci"]
    assert lo < 0.09 < hi
    assert s["consistency"] == 0.91
