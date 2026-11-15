import pytest
from truss.taxonomy import (Mode, Taxonomy, clean_traces_to_retire, clusters, coverage, kappa,
                            wilson, zero_bound, drift, check_coverage)


def base():
    t = Taxonomy("0.1")
    for code, name in (("FM-01", "a"), ("FM-02", "b"), ("FM-03", "c")):
        t.modes[code] = Mode(code, name, ("hardship",), name, test=f"{name}?", layer=3, owner="o")
    return t


def test_split_closes_parent_and_crosswalks():
    t = base()
    t.split("FM-02", [Mode("FM-04", "b1", ("hardship",), "", test="?", layer=1, owner="o"),
                      Mode("FM-05", "b2", ("hardship",), "", test="?", layer=2, owner="o")], "two causes")
    assert t.modes["FM-02"].status == "closed"
    assert t.crosswalk()["FM-02"] == ["FM-04", "FM-05"]
    assert t.release()["to"] == "0.2" and not t.validate()


def test_codes_never_reused_and_reason_required():
    t = base()
    with pytest.raises(ValueError):
        t.add(Mode("FM-01", "x", ("fee",), ""), "dup")
    with pytest.raises(ValueError):
        t.add(Mode("FM-09", "x", ("fee",), ""), "")


def test_retire_needs_guard_and_patch_cannot_change_membership():
    t = base()
    with pytest.raises(ValueError):
        t.retire("FM-03", "", "gone")
    t.retire("FM-03", "L1 index check", "cause removed")
    with pytest.raises(ValueError):
        t.release("patch")


def test_patch_rewords_only():
    t = base()
    d0 = t.digest()
    t.reword("FM-01", "clearer", test="a, asked before income?")
    rec = t.release("patch")
    assert rec["to"] == "0.1.1" and rec["digest"] != d0
    with pytest.raises(ValueError):
        t.reword("FM-01", "x", status="retired")


def test_merge_resolves_transitively_and_json_round_trip():
    t = base()
    t.merge(["FM-01", "FM-02"], Mode("FM-04", "ab", ("hardship",), "", test="?", layer=1, owner="o",
                                     facets=("a", "b")), "same check")
    t.split("FM-04", [Mode("FM-05", "x", ("hardship",), "", test="?", layer=1, owner="o"),
                      Mode("FM-06", "y", ("hardship",), "", test="?", layer=1, owner="o")], "later")
    assert t.crosswalk()["FM-01"] == ["FM-05", "FM-06"]
    u = Taxonomy.from_json(t.to_json())
    assert u.digest() == t.digest() and u.modes["FM-04"].facets == ("a", "b")


def test_measures():
    labs = [{"code": "FM-01", "fit": True}] * 8 + [{"code": "FM-02", "fit": False}] + [{"code": None, "fit": False}]
    c = coverage(labs)
    assert (c["naive"], c["fitted_share"]) == (0.9, 0.8)
    assert abs(zero_bound(20) - 0.139) < 0.001 and clean_traces_to_retire(0.02) == 149
    assert kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    lo, hi = wilson(0, 20)
    assert lo == 0 and 0.16 < hi < 0.17
    assert drift({"X": (1, 100)}, {"X": (12, 50)})[0]["flag"] == "rose"
    assert len(clusters(["queue closed no callback", "queue closed after hours no callback",
                         "spanish request missed"])) == 2
    t = base()
    assert check_coverage(t, {"FM-01": [1], "FM-02": [4]})["with_check"] == 1
