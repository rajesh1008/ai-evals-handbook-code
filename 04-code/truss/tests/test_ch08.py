import pytest
from truss.metrics import (Card, Refused, Registry, before_after, composite, length_bias, length_table, measure,
                           move_needed, paired, to_markdown, weighted_kappa)


def reg():
    return Registry({"FM-01": "active", "FM-02": "active", "FM-05": "retired"},
                    {"FM-01": ["t-000001"]}, "abc")


def card(**k):
    d = dict(id="MC-01", name="m", modes=("FM-01",), question="q?", population="p", kind="code",
             tier="gate", owner="o", validated="read", rule="no_new_fail")
    d.update(k)
    return Card(**d)


def test_registry_refuses_metrics_without_trace_evidence():
    r = reg()
    r.add(card())
    with pytest.raises(Refused, match="no trace evidence"):
        r.add(card(id="MC-02", modes=("FM-02",)))
    with pytest.raises(Refused, match="retired"):
        r.add(card(id="MC-03", modes=("FM-05",)))
    with pytest.raises(Refused, match="no failure mode"):
        r.add(card(id="P-01", modes=(), tier="monitor", rule=""))
    with pytest.raises(Refused, match="one metric per failure mode"):
        r.add(card(id="MC-04", tier="monitor", rule=""))
    with pytest.raises(Refused, match="validated"):
        Registry({"FM-01": "active"}, {"FM-01": ["t"]}).add(card(validated=""))
    r.add(Card("S-01", "csat", (), "", "all", "signal", "inform", "x"))
    assert list(r.cards) == ["MC-01", "S-01"] and len(r.refused) == 4 and r.unmetered() == ["FM-02"]
    with pytest.raises(ValueError):
        card(rule="")


def test_measure_counts_deferred_where_the_card_says():
    o = ["pass"] * 90 + ["fail"] * 5 + ["deferred"] * 4 + ["cannot_tell"]
    assert measure(card(deferred_as="fail"), o)["fail"] == 9
    m = measure(card(deferred_as="pass"), o)
    assert (m["fail"], m["n"], m["deferred"], m["cannot_tell"]) == (5, 99, 4, 1)
    assert measure(card(deferred_as="excluded"), o)["n"] == 95
    c = card(target=0.02).amend("2027-03-10", "x", deferred_as="pass")
    assert c.version == "1.1" and measure(c, ["pass"] * 149)["meets_target"] is True
    assert "v1.1" in to_markdown(c)


def test_length_table_and_bias_flag():
    rows = [{"w": w, "s": w / 300, "f": w % 7 == 0} for w in range(40, 300)]
    t = length_table(rows, "s", "f", "w", [("short", 0, 100), ("long", 100, 1000)])
    assert t[0]["mean_score"] < t[1]["mean_score"] and t[0]["n"] + t[1]["n"] == 260
    assert length_bias(rows, "s", "f", "w")["flag"]


def test_composite_and_move_needed():
    v, parts = composite({"a": 0.9, "b": 0.5}, {"a": 3, "b": 1})
    assert abs(v - 0.8) < 1e-9 and abs(parts["b"] - 0.125) < 1e-9
    assert abs(move_needed({"a": 3, "b": 1})["b"] - 0.04) < 1e-9


def test_before_after_holds_on_any_new_failure_under_no_new_fail():
    base = {"MC-01": {"t1": "pass", "t2": "fail", "t3": "fail", "t4": "pass"}}
    cand = {"MC-01": {"t1": "fail", "t2": "pass", "t3": "pass", "t4": "pass"}}
    assert paired(base["MC-01"], cand["MC-01"]) == (["t1"], ["t2", "t3"])
    rows, d, holds = before_after([card()], base, cand)
    assert d == "hold" and rows[0]["newly_fail"] == ["t1"] and "t1" in holds[0]
    rows, d, _ = before_after([card(rule="paired")], base, cand)
    assert d == "ship"


def test_weighted_kappa():
    assert weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == 1.0
    assert weighted_kappa([1, 2, 3, 4, 5], [2, 3, 4, 5, 5]) < 1.0
