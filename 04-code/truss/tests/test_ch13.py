import pytest
from truss import adjudication as J

L = lambda t, who, lab, g="r3": J.Label(t, who, lab, g)


def test_agreed_and_disagreement_needs_ruling():
    r = J.adjudicate("t1", L("t1", "g", "x"), L("t1", "b", "x"), adjudicator="d", guideline="r3", policy="P", decided_on="d")
    assert r.kind == "agreed" and r.gold == "x" and r.labels == (("A", "x"), ("B", "x"))
    with pytest.raises(ValueError):
        J.adjudicate("t2", L("t2", "g", "x"), L("t2", "b", "y"), adjudicator="d", guideline="r3", policy="P", decided_on="d")
    with pytest.raises(ValueError):
        J.adjudicate("t2", L("t2", "g", "x"), L("t2", "b", "y"), {"gold": "x", "kind": "slip", "rationale": " "},
                     adjudicator="d", guideline="r3", policy="P", decided_on="d")


def test_audit_reopens_an_agreement():
    with pytest.raises(ValueError):
        J.adjudicate("t1", L("t1", "g", "x"), L("t1", "b", "x"), adjudicator="d", guideline="r3", policy="P",
                     decided_on="d", audit="policy code says y")


def test_policy_ruling_pending_until_id_then_rederive():
    r = J.adjudicate("t3", L("t3", "g", "x"), L("t3", "b", "x"), {"gold": "x", "kind": "policy", "rationale": "silent",
                     "escalated_to": "Victor"}, adjudicator="d", guideline="r3", policy="P", decided_on="d", audit="code y")
    assert r.status == "pending" and r.gold is None
    with pytest.raises(ValueError):
        J.gold([r])
    with pytest.raises(ValueError):
        J.adjudicate("t3", L("t3", "g", "x"), L("t3", "b", "y"), {"gold": "x", "kind": "policy", "rationale": "silent"},
                     adjudicator="d", guideline="r3", policy="P", decided_on="d")
    d0 = r.digest()
    J.rederive(r, "x", policy="P2", ruling_id="R-1", decided_on="d2", why="ruling R-1")
    assert J.gold([r]) == {"t3": "x"} and r.history[0]["digest"] == d0 and r.digest() != d0


def test_cannot_tell_leaves_the_set():
    r = J.adjudicate("t4", L("t4", "g", "x"), L("t4", "b", "y"), {"gold": J.CANNOT_TELL, "kind": "fact", "rationale": "loan not named"},
                     adjudicator="d", guideline="r3", policy="P", decided_on="d")
    assert r.status == J.CANNOT_TELL and J.gold([r]) == {}


def test_kappa_alpha_agreement():
    a = list("aaaaaaaabb"); b = list("aaaaaaaaab")
    assert J.percent_agreement(a, b) == 0.9
    assert abs(J.kappa(a, b) - 0.6153846) < 1e-6
    al = J.alpha([[x, y] for x, y in zip(a, b)])
    assert al == pytest.approx(1 - 2 / (17 * 3 * 2 / 19))  # pooled marginals, n - 1 correction
    assert J.alpha([["a", "a"], ["b", "b"]]) == 1.0
    assert J.matrix(a, b, ["a", "b"]) == [[8, 0], [1, 1]]
    assert J.per_label_kappa(a, b, ["a", "b"])["a"] == pytest.approx(J.kappa(a, b))


def test_alpha_known_value():
    # Krippendorff (2011) nominal example reduced to two coders, no missing values
    units = [["a", "a"], ["b", "b"], ["b", "c"], ["c", "c"], ["a", "a"], ["b", "b"], ["c", "a"], ["c", "c"]]
    o_dis = 4  # two disagreeing units, each pair counted both ways
    n = 16
    nc = {"a": 5, "b": 5, "c": 6}
    de = sum(nc[x] * nc[y] for x in nc for y in nc if x != y) / (n - 1)
    assert J.alpha(units) == pytest.approx(1 - o_dis / de)


def test_hours_minutes_anchor():
    labs = [J.Label("t1", "g", "x", "r3", minutes=30, minute_in_sitting=10, labelled_on="w1"),
            J.Label("t1", "b", "y", "r3", minutes=30, minute_in_sitting=70, labelled_on="w1")]
    h = J.expert_hours(labs, [("d", "adjudication", 60)])
    assert h["hours"] == 2 and h["dollars"] == 120
    bm = J.by_minute(J.pairs([labs[0]], [labs[1]]))
    assert bm[-1]["disagree"] == 1 and sum(r["n"] for r in bm) == 1
    an = J.anchor_agreement({"t1": "x"}, labs)
    assert an[("g", "w1")]["rate"] == 1 and an[("b", "w1")]["rate"] == 0
    m = J.manifest([J.adjudicate("t1", labs[0], labs[0], adjudicator="d", guideline="r3", policy="P", decided_on="d")], "g", "1")
    assert m["kinds"] == {"agreed": 1} and len(m["digest"]) == 12
