"""Tests for truss.drift (Chapter 19). Seven tests, matching prior chapters."""
from truss.drift import (
    THRESHOLDS, week_report, track_split, rolling_median, alert, diagnose,
    slice_disagreements, version_record, same_version, change_control, revalidate,
)


def _expand(tp, fn, fp, tn, pos="fail", neg="pass"):
    truth = [pos] * tp + [pos] * fn + [neg] * fp + [neg] * tn
    pred = [pos] * tp + [neg] * fn + [pos] * fp + [neg] * tn
    return truth, pred


def test_week_report_kappa_on_known_matrix():
    # TP=17 FN=3 FP=3 TN=77 -> agreement 0.94, kappa 0.8125 (hand-checked).
    truth, pred = _expand(17, 3, 3, 77)
    r = week_report(truth, pred)
    assert r["n"] == 100 and r["tp"] == 17 and r["fn"] == 3 and r["fp"] == 3 and r["tn"] == 77
    assert r["agree_n"] == 94 and abs(r["agreement"] - 0.94) < 1e-12
    assert abs(r["kappa"] - 0.8125) < 1e-12
    assert abs(r["tpr"] - 17 / 20) < 1e-12 and abs(r["tnr"] - 77 / 80) < 1e-12


def test_week_report_kappa_on_harbor_drop():
    # The Chapter 19 scoreboard drop: TP=22 FN=6 FP=10 TN=62 -> kappa 0.62.
    truth, pred = _expand(22, 6, 10, 62)
    r = week_report(truth, pred)
    assert r["agree_n"] == 84
    assert round(r["kappa"], 2) == 0.62
    assert abs(r["kappa"] - 0.6197718631178706) < 1e-12


def test_track_split_pools_and_gap():
    frozen_t, frozen_p = _expand(7, 1, 1, 31)
    fresh_t, fresh_p = _expand(15, 5, 9, 31)
    rows = ([{"track": "frozen", "truth": t, "pred": p} for t, p in zip(frozen_t, frozen_p)]
            + [{"track": "fresh", "truth": t, "pred": p} for t, p in zip(fresh_t, fresh_p)])
    s = track_split(rows)
    assert s["frozen"]["n"] == 40 and s["fresh"]["n"] == 60 and s["pooled"]["n"] == 100
    assert s["pooled"]["tp"] == 22 and s["pooled"]["fn"] == 6
    assert s["pooled"]["fp"] == 10 and s["pooled"]["tn"] == 62
    assert round(s["pooled"]["kappa"], 2) == 0.62
    assert abs(s["gap"] - (s["frozen"]["kappa"] - s["fresh"]["kappa"])) < 1e-12


def test_alert_detects_world_moved_on_policy_drop():
    def split_of(ftp, ffn, ffp, ftn, stp, sfn, sfp, stn):
        ft, fp = _expand(ftp, ffn, ffp, ftn)
        st, sp = _expand(stp, sfn, sfp, stn)
        rows = ([{"track": "frozen", "truth": t, "pred": p} for t, p in zip(ft, fp)]
                + [{"track": "fresh", "truth": t, "pred": p} for t, p in zip(st, sp)])
        return track_split(rows)

    history = [
        split_of(7, 1, 1, 31, 10, 2, 2, 46),  # w1 pooled 17/3/3/77, kappa 0.8125
        split_of(7, 1, 1, 31, 11, 2, 3, 44),
        split_of(7, 1, 1, 31, 10, 1, 2, 47),
    ]
    dropped = split_of(7, 1, 1, 31, 15, 5, 9, 31)  # w4
    a = alert(history, dropped)
    assert a["verdict"] == "fail"
    assert a["diagnostic"] == "world_moved"
    assert round(a["kappa"], 2) == 0.62
    assert a["drop"] >= THRESHOLDS["drop_fail"]
    assert a["gap"] >= THRESHOLDS["track_gap_flag"]
    # Frozen did not move, so the cause is not the judge.
    assert a["frozen_drop"] < THRESHOLDS["drop_flag"]


def test_version_record_digest_is_stable_and_content_addressed():
    a = version_record(
        "fee-judge-v1", "prompt-v1", "model-pin-1",
        {"waive_or_charge": "old"}, "HP-2027-04", "MC-02 v1.1", "decide",
        admitted_on="2027-11-15")
    b = version_record(
        "fee-judge-v1", "prompt-v1", "model-pin-1",
        {"waive_or_charge": "old"}, "HP-2027-04", "MC-02 v1.1", "decide",
        admitted_on="2027-12-01")  # date not hashed
    c = version_record(
        "fee-judge-v2", "prompt-v1", "model-pin-1",
        {"waive_or_charge": "new"}, "HB-2027-12", "MC-02 v1.1", "decide",
        admitted_on="2027-12-17")
    assert same_version(a, b)
    assert len(a["digest"]) == 12 and all(ch in "0123456789abcdef" for ch in a["digest"])
    assert not same_version(a, c)


def test_change_control_holds_silent_deletion_and_passes_ruled_rewrite():
    old = [
        {"id": "loan", "text": "name the loan on the span"},
        {"id": "waive_or_charge", "text": "fees apply unless an officer waives"},
        {"id": "tone", "text": "optional courtesy"},
    ]
    deleted = [c for c in old if c["id"] != "loan"]
    held = change_control(old, deleted, frozen_ids={"loan", "waive_or_charge"})
    assert held["verdict"] == "hold" and held["deleted_frozen"] == ["loan"]

    rewritten = [
        {"id": "loan", "text": "name the loan on the span"},
        {"id": "waive_or_charge", "text": "plan fees are waived automatically"},
        {"id": "tone", "text": "optional courtesy"},
    ]
    silent = change_control(old, rewritten, frozen_ids={"loan", "waive_or_charge"})
    assert silent["verdict"] == "hold" and silent["rewritten_unapproved"] == ["waive_or_charge"]
    ruled = change_control(
        old, rewritten, frozen_ids={"loan", "waive_or_charge"},
        allowed_rewrites={"waive_or_charge": "HB-2027-12"})
    assert ruled["verdict"] == "pass"
    assert ruled["rewritten_approved"] == ["waive_or_charge"]
    assert ruled["rulings"]["waive_or_charge"] == "HB-2027-12"


def test_revalidate_and_slice_disagreements():
    # A 100-trace peek cannot clear Chapter 16's Wilson floors even when
    # it looks healthy; re-validation uses a 200-trace set.
    peek = week_report(*_expand(17, 3, 3, 77))
    assert round(peek["kappa"], 2) == 0.81
    assert revalidate(peek)["verdict"] == "refuse"

    good = week_report(*_expand(46, 4, 6, 144))
    v = revalidate(good)
    assert v["verdict"] == "admit" and v["reasons"] == []
    assert v["tpr_lo"] >= 0.80 and v["tnr_lo"] >= 0.90
    assert good["n"] == 200 and good["kappa"] >= 0.75

    bad = week_report(*_expand(22, 6, 10, 62))  # the dropped week
    refused = revalidate(bad)
    assert refused["verdict"] == "refuse"
    assert "kappa" in refused["reasons"]

    rows = (
        [{"slice": "plan_fee", "truth": "fail", "pred": "pass"}] * 5
        + [{"slice": "plan_fee", "truth": "pass", "pred": "fail"}] * 9
        + [{"slice": "plan_fee", "truth": "fail", "pred": "fail"}] * 2
        + [{"slice": "plan_fee", "truth": "pass", "pred": "pass"}] * 4
        + [{"slice": "other", "truth": "fail", "pred": "fail"}] * 13
        + [{"slice": "other", "truth": "pass", "pred": "pass"}] * 27
    )
    s = slice_disagreements(rows)
    assert s["plan_fee"]["n"] == 20 and s["plan_fee"]["disagree"] == 14
    assert s["other"]["disagree"] == 0
    assert abs(s["plan_fee"]["disagree_rate"] - 0.7) < 1e-12
