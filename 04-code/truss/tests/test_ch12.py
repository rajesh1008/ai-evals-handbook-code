from truss.datasets import (case_digest, set_digest, diff, rate_eligible, near_duplicates,
                            leak_scan, slice_gate, mdd, graduate, stale_labels, manifest)


def _c(i, **kw):
    c = {"case_id": f"g-{i:04d}", "flow": "hardship", "slice": "common", "source": "production",
         "label": "pass", "text": f"case number {i} about a deferral on loan {i}"}
    c.update(kw)
    return c


def test_digest_is_order_free_and_sees_relabels():
    a = [_c(1), _c(2)]
    assert set_digest(a) == set_digest(a[::-1])
    b = [_c(1), _c(2, label="fail")]
    assert set_digest(a) != set_digest(b)
    d = diff(a, b + [_c(3)])
    assert d["added"] == ["g-0003"] and d["relabelled"] == ["g-0002"] and not d["removed"]


def test_incident_synthetic_planted_never_counted():
    assert rate_eligible(_c(1))
    assert not any(rate_eligible(_c(1, source=s)) for s in ("incident", "synthetic", "planted", "authored"))
    m = manifest("golden", "1.0", [_c(1), _c(2, source="incident")])
    assert m["n"] == 2 and m["rate_eligible"] == 1


def test_near_duplicates_and_leak_scan():
    t = ["I lost my job and cannot pay my auto loan this month",
         "I lost my job and cannot pay my auto loan this month at all",
         "My shop flooded in March"]
    assert [(i, j) for i, j, _ in near_duplicates(t, 0.5)] == [(0, 1)]
    cases = [{"case_id": "g-1", "text": t[0]}, {"case_id": "g-2", "text": t[2]}]
    docs = {"kb-1": "Worked example. " + t[0] + " Answer: draft_deferral.", "kb-2": "Policy 4.3 window."}
    hits = leak_scan(docs, cases, n=5)
    assert [(h[0], h[1]) for h in hits] == [("kb-1", "g-1")]
    assert leak_scan({"kb-3": "zz-canary-41 shop"}, cases, n=5, canaries=("zz-canary-41",)) == []


def test_slice_gate_is_and_of_slices_not_aggregate():
    res = [("common", True)] * 400 + [("adversarial", True)] * 30 + [("adversarial", False)] * 20
    g = slice_gate(res, {"common": 0.95, "adversarial": 0.8})
    assert g["aggregate"] > 0.95 and g["slices"]["common"]["pass"] and not g["pass"]


def test_mdd_shrinks_with_n():
    assert mdd(100) > mdd(400) > mdd(1600)
    assert abs(mdd(400) / mdd(1600) - 2) < 1e-9


def test_graduation_and_stale_labels():
    h = {"a": [False, True, True, True], "b": [True, True, False], "c": [True, True]}
    assert graduate(h, 3) == ["a"]
    cs = [_c(1, labelled_on="2027-03-10", features={"prior_relief": True}),
          _c(2, labelled_on="2027-04-20", features={"prior_relief": True}), _c(3, labelled_on="2027-01-01")]
    ch = [{"policy": "HP-2027-04", "effective": "2027-04-01", "flow": "hardship", "feature": "prior_relief"}]
    assert stale_labels(cs, ch) == [("g-0001", "HP-2027-04")]
    assert case_digest(cs[0]) != case_digest(cs[1])
