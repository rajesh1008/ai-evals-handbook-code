import pytest

from truss.judge import (JudgeSpec, MissingInput, Leak, render, parse, split, guard, confusion, rates,
                         agreement_kappa, flips, majority, pair_outcome, call_cost, percentile, month, admit)

SPEC = JudgeSpec("MC-02", "1.1", "Did the reply state a fee amount ... that differs?",
                 ["Compare the loan number.", "Tool error: deferral passes."], model="small")


def test_render_refuses_missing_span_and_keeps_critique_first():
    with pytest.raises(MissingInput, match="tool_span"):
        render(SPEC, {"question": "q", "reply": "r"})
    p = render(SPEC, {"question": "q", "tool_span": "fee_lookup -> {}", "reply": "r"})
    assert "1. Compare the loan number." in p and p.index("critique") < p.index('{"verdict"')


def test_parse_takes_last_json_and_never_coerces():
    assert parse('Critique {"x": 1}. \n{"verdict": "FAIL"}') == "fail"
    assert parse('{"verdict": "probably fine"}') == "unparsed" and parse("no json") == "unparsed"


def test_split_is_stratified_and_guard_catches_leaks():
    items = [("a", i) for i in range(9)] + [("b", i) for i in range(3)]
    dev, test = split(items, kind=lambda x: x[0])
    assert len(dev) == 4 and len(test) == 8 and sum(k == "b" for k, _ in dev) == 1
    assert guard(["d1", "d2"], ["t1"])
    with pytest.raises(Leak, match="t1"):
        guard(["d1", "t1"], ["t1", "t2"])


def test_confusion_counts_abstentions_as_misses():
    truth = ["fail", "fail", "fail", "pass", "pass", "pass"]
    pred = ["fail", "cannot_tell", "pass", "pass", "fail", "unparsed"]
    cm = confusion(truth, pred)
    assert cm == {"tp": 1, "fn": 1, "fp": 1, "tn": 1, "abstain_pos": 1, "abstain_neg": 1}
    r = rates(cm)
    assert r["tpr"] == pytest.approx(1 / 3) and r["tnr"] == pytest.approx(1 / 3) and r["precision"] == 0.5
    assert 0 < r["tpr_ci"][0] < r["tpr"] < r["tpr_ci"][1] < 1
    assert agreement_kappa(["fail", "pass"] * 5, ["fail", "pass"] * 5) == 1.0


def test_flips_majority_and_pairs():
    runs = [["fail", "pass", "pass"], ["fail", "fail", "pass"], ["fail", "pass", "cannot_tell"]]
    f = flips(runs)
    assert f["flipped"] == 2 and f["where"] == [1, 2]
    assert majority(runs) == ["fail", "pass", "pass"]
    assert majority([["fail"], ["pass"]]) == ["cannot_tell"]
    assert pair_outcome("A", "B") == "original" and pair_outcome("B", "A") == "other"
    assert pair_outcome("A", "A") == "position" and pair_outcome("tie", "tie") == "tie"


def test_cost_and_month():
    assert call_cost(1_000_000, 0, 1.0, 5.0) == 1.0 and call_cost(0, 200_000, 1.0, 5.0) == 1.0
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    m = month(3000, 0.002, 0.10, read_minutes=2, reader_rate=60)
    assert m["judge_cost"] == pytest.approx(6.0) and m["ordered_reads"] == pytest.approx(300)
    assert m["read_ordered_cost"] == pytest.approx(600) and m["read_everything"] == pytest.approx(6000)


def test_admit_orders_but_never_decides_without_a_report_card():
    good = {"tpr_ci": (0.86, 0.99), "tnr_ci": (0.95, 1.0)}
    assert admit(SPEC, good, role="order") == {"admit": True, "role": "order", "card": "MC-02 v1.1", "reasons": []}
    d = admit(SPEC, good, role="decide")
    assert not d["admit"] and d["role"] == "none" and "Judge Report Card" in d["reasons"][0]
    assert admit(SPEC, good, role="decide", report_card="JRC-1")["admit"]
    weak = admit(SPEC, {"tpr_ci": (0.6, 0.9), "tnr_ci": (0.95, 1.0)}, role="order")
    assert not weak["admit"] and weak["reasons"][0].startswith("TPR lower bound 0.60")
    assert not admit(SPEC, good, role="order", tested_on_test=False)["admit"]
