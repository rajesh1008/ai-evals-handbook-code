import pytest
from truss.notebook import (Entry, adjudicate, agreement, cluster_decision, code_session, frame_audit,
                            hours, pps_quota, read, saturation, share_check)


def frame():
    return [{"trace_id": f"t-{i:03d}", "flow": "a" if i % 3 else "b", "turns": i % 7 + 1,
             "status": "error" if i % 10 == 0 else "completed", "err": i % 10 == 0} for i in range(300)]


def test_quota_draw_is_exact_and_reproducible():
    f = frame()
    d1 = pps_quota(f, "flow", {"a": 12, "b": 8}, lambda r: r["turns"], seed=7)
    d2 = pps_quota(f, "flow", {"a": 12, "b": 8}, lambda r: r["turns"], seed=7)
    assert d1 == d2 and len(d1) == 20 and len({t for t, _, _ in d1}) == 20
    assert [s for _, s, _ in d1] == ["a"] * 12 + ["b"] * 8


def test_frame_audit_refuses_undeclared_exclusion():
    f = frame()
    ok = frame_audit(f, [r["trace_id"] for r in f])
    bad = frame_audit(f, [r["trace_id"] for r in f if r["status"] == "completed"])
    assert ok["ok"] and not bad["ok"] and bad["undeclared"] == ["error"] and bad["excluded"]["error"] == 30
    assert frame_audit(f, [r["trace_id"] for r in f if r["status"] == "completed"], declared=("error",))["ok"]
    assert not share_check(f, [r["trace_id"] for r in f if not r["err"]][:40], "err")["ok"]


def test_saturation_and_agreement():
    a = [Entry(1, "t1", "a", "fail", open_code="x", cluster="X"), Entry(2, "t2", "a", "pass"),
         Entry(3, "t3", "a", "fail", code="FM-01"), Entry(4, "t4", "a", "fail", cluster="X")]
    b = [Entry(1, "t1", "a", "fail", code="FM-02"), Entry(2, "t2", "a", "pass"),
         Entry(3, "t3", "a", "fail", code="FM-01"), Entry(4, "t4", "a", "pass")]
    assert saturation(a) == [(1, 1, 1), (2, 1, 1), (3, 2, 2), (4, 3, 2)]
    ag = agreement(a, b)
    assert ag["label_agree"] == 2 and [d["kind"] for d in ag["disagreements"]] == ["code", "verdict"]


def test_adjudication_needs_ruling_decider_and_reason():
    dis = [{"n": 1, "trace_id": "t1", "first": "open:X", "second": "FM-02", "kind": "code"}]
    with pytest.raises(ValueError):
        adjudicate(dis, {})
    with pytest.raises(ValueError):
        adjudicate(dis, {1: ("vote", "FM-02", "majority", "two of three")})
    out = adjudicate(dis, {1: ("facts", "FM-02", "the trace", "tool output says so")})
    assert out[0]["second_right"] and not out[0]["first_right"]


def test_cluster_rule():
    assert cluster_decision(False, False, True, 5) == "noise"
    assert cluster_decision(True, True, True, 1) == "existing mode"
    assert cluster_decision(True, False, False, 4) == "split before adding"
    assert cluster_decision(True, False, True, 1) == "open code"
    assert cluster_decision(True, False, True, 1, confirmed_elsewhere=1) == "new mode"
    assert cluster_decision(True, False, True, 1, critical=True) == "new mode"


def test_cli_session_resumes_and_hours(tmp_path):
    traces = [{"trace_id": f"t{i}", "flow": "a", "turns": 2} for i in range(3)]
    nb = tmp_path / "nb.csv"
    code_session(traces[:2], nb, "me", iter(["p fine", "f wrong loan :: fee for other loan"]), out=open("/dev/null", "w"))
    code_session(traces, nb, "me", iter(["c unsure"]), out=open("/dev/null", "w"))
    e = read(nb)
    assert [x.verdict for x in e] == ["pass", "fail", "cannot_tell"] and e[1].open_code == "wrong loan"
    with pytest.raises(ValueError):
        code_session([{"trace_id": "t9", "flow": "a", "turns": 1}], tmp_path / "x.csv", "me", iter(["f "]), out=open("/dev/null", "w"))
    h = hours([("read", "lead", 10, 6), ("read", "officer", 5, 12)], {"lead": 85, "officer": 60})
    assert h["hours"] == 2 and h["dollars"] == 85 + 60
