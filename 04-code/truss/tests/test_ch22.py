"""Tests for truss.rationale (Chapter 22). Seven tests, matching prior chapters."""
from truss.rationale import (extract_dates, style_features, dates_not_in_trace, consistency, cutoff, claim_check,
                             association, fit_flag_rule, evaluate_flag, cue_effect, divergence, explanation_cost)


def test_extract_dates_and_trace_check():
    t = "The waiver on 2027-03-04 and the fee on February 19, 2028; cut-off 2027-02-19."
    assert extract_dates(t) == {"2027-03-04", "2028-02-19", "2027-02-19"}
    assert dates_not_in_trace(t, {"2027-03-04", "2028-02-19"}, allowed={"2027-02-19"}) == []
    assert dates_not_in_trace("cut-off 2027-02-09", {"2028-02-24"}) == ["2027-02-09"]


def test_style_features_and_consistency():
    f = style_features("It may appear late; actually the fee stands.")
    assert f["hedges"] == 2 and f["self_correction"] and f["words"] == 8
    assert consistency("pass", "fail") == "contradicts" and consistency("fail", "fail") == "consistent"
    assert consistency("unclear", "pass") == "unclear"


def test_cutoff_and_claim_check():
    assert cutoff("2028-02-19") == "2027-02-19" and cutoff("2028-02-29") == "2027-02-28"
    rec = {"fee_date": "2028-02-19", "waiver_date": "2027-03-04", "window": "inside"}
    r = claim_check({"cutoff_date": "2027-02-19", "waiver_date": "2027-03-04", "window": "outside"}, rec)
    assert r == {"checked": ["cutoff", "waiver_date", "window"], "wrong": ["window"]}
    assert claim_check({"cutoff_date": None, "window": "not_discussed"}, rec) == {"checked": [], "wrong": []}


def test_association_rates_and_coverage():
    a = association([True, True, False, False, False], [1, 0, 1, 0, 0])
    assert a["present"] == 2 and a["present_err"] == 1 and a["absent_err"] == 1
    assert abs(a["errors_covered"] - 0.5) < 1e-12 and abs(a["lift"] - 1.5) < 1e-12


def test_flag_rule_fits_within_budget_and_scores_production():
    rows = [{"err": 1, "a": True}, {"err": 1, "b": True}, {"err": 0, "b": True}, {"err": 0, "c": True}] + [{"err": 0}] * 6
    fit = fit_flag_rule(rows, ["a", "b", "c"], budget=0.2)
    assert fit["rule"] == ["a"] and fit["caught"] == 1 and fit["flagged"] == 1
    fit = fit_flag_rule(rows, ["a", "b", "c"], budget=0.3)
    assert fit["rule"] == ["a", "b"] and fit["caught"] == 2
    ev = evaluate_flag(rows, ["a", "b"], production=lambda r: not r.get("c"))
    assert ev["caught"] == 2 and ev["flagged"] == 3 and ev["prod_n"] == 9 and ev["prod_flagged"] == 3


def test_cue_effect_against_noise():
    base = ["fail"] * 8 + ["pass"] * 2
    rep = ["fail"] * 7 + ["pass"] * 3
    cued = ["pass"] * 3 + ["fail"] * 5 + ["pass"] * 2
    ack = [False] * 10
    e = cue_effect(base, rep, cued, ack)
    assert e["noise_flips"] == 1 and e["cue_flips"] == 3 and e["toward"] == 3 and e["ack_in_flips"] == 0
    assert abs(e["excess"] - 0.2) < 1e-12


def test_divergence_refuses_better_prose_worse_verdicts_and_cost():
    d = divergence({"convincing": 4.0, "errors": 25, "n": 200}, {"convincing": 4.1, "errors": 57, "n": 200})
    assert not d["admit"] and d["quality_up"] and len(d["reasons"]) == 2
    assert divergence({"convincing": 4.0, "errors": 25, "n": 200}, {"convincing": 3.9, "errors": 20, "n": 200})["admit"]
    c = explanation_cost(54765, 30996, 300, 5.0, 3514)
    assert abs(c["extra_tokens_per_call"] - 79.23) < 0.01 and round(c["extra_per_month"], 2) == 1.39
