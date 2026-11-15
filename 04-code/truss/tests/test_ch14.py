import pytest

from truss.annotation import (assign, load_by_reader, pairwise, fleiss_kappa, final_labels, select,
                              ht_rate, cost_per_label, debt, session_record, anchor_table)

R = ("marisol", "daniel", "kevin")


def test_assign_overlap_anchors_and_must_include():
    ids = [f"t-{i}" for i in range(100)]
    jobs = assign(ids, R, triple=0.2, anchors=["a-1", "a-2"], must_include=lambda t: "marisol" if t.endswith("7") else None)
    per = {}
    for _, t, r in jobs:
        per.setdefault(t, set()).add(r)
    assert sum(len(v) == 3 for t, v in per.items() if t.startswith("t-")) == 20
    assert all(len(v) >= 2 for v in per.values())
    assert per["a-1"] == set(R) and per["a-2"] == set(R)
    assert all("marisol" in per[t] for t in ids if t.endswith("7"))
    assert sum(load_by_reader(jobs).values()) == len(jobs)


def test_fleiss_matches_hand_example():
    units = [["a", "a", "a"], ["a", "b", "b"], ["b", "b", "b"], ["a", "a", "b"]]
    # p_i = 1, 1/3, 1, 1/3 -> mean 2/3; p_a = p_b = 1/2 -> p_e = 1/2; kappa = 1/3
    assert fleiss_kappa(units, ["a", "b"]) == pytest.approx(1 / 3)


def test_pairwise_and_anchor_table():
    rd = {"t1": {"marisol": "x", "daniel": "x"}, "t2": {"marisol": "y", "daniel": "x", "kevin": "y"}}
    pw = pairwise(rd, R)
    assert pw[("marisol", "daniel")]["n"] == 2 and pw[("marisol", "daniel")]["agree"] == 1
    assert pw[("daniel", "kevin")]["n"] == 1
    at = anchor_table(rd, {"t2": "y"}, R)
    assert at["marisol"]["right"] == 1 and at["daniel"]["right"] == 0


def test_final_labels_need_rulings():
    rd = {"t1": {"a": "x", "b": "x"}, "t2": {"a": "x", "b": "y"}}
    out, pending = final_labels(rd, {})
    assert out == {"t1": "x"} and pending == ["t2"]
    out, pending = final_labels(rd, {"t2": "y"})
    assert out["t2"] == "y" and not pending


def test_targeted_draw_refuses_a_rate_but_mixed_does_not():
    frame = [f"t-{i}" for i in range(200)]
    failed = {t: int(i % 10 == 0) for i, t in enumerate(frame)}
    ids, inc = select(frame, 20, "failure", score=lambda t: failed[t])
    with pytest.raises(ValueError):
        ht_rate(failed, inc, len(frame))
    ids, inc = select(frame, 40, "mixed", score=lambda t: failed[t], mix_targeted=10)
    assert len(ids) == 40 and 0 <= ht_rate(failed, inc, len(frame)) <= 1


def test_cost_debt_and_session_record():
    c = cost_per_label({"marisol": 120}, {"marisol": 60.0}, 10, [("adjudication", 30.0)])
    assert c["per_label"] == pytest.approx(15.0)
    d = debt([{"kind": "unadjudicated", "items": 12, "minutes_each": 5, "blocks": True},
              {"kind": "audit due", "items": 30, "minutes_each": 4}])
    assert d["total_hours"] == pytest.approx(3.0) and d["blocking_items"] == 12
    with pytest.raises(AssertionError):
        session_record("2027-08-13", ("decline_window", "draft_deferral"), 6, "guideline silent")
    r = session_record("2027-08-13", ("decline_window", "draft_deferral"), 6, "guideline silent",
                       change="add the anniversary example", sentence="G-06")
    assert len(r["id"]) == 12


def test_pool_mixed_design_is_unbiased_on_average():
    frame = [f"t-{i:03d}" for i in range(300)]
    failed = {t: int(i % 7 == 0) for i, t in enumerate(frame)}
    pool = [t for i, t in enumerate(frame) if i % 7 == 0 or i % 5 == 0]
    est = [ht_rate(failed, select(frame, 40, "mixed", seed=s, mix_targeted=10, pool=pool)[1], len(frame)) for s in range(400)]
    assert abs(sum(est) / len(est) - sum(failed.values()) / len(frame)) < 0.01
