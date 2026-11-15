from truss.reportcard import (
    rogan_gladen, rogan_gladen_interval, ppi, ppi_interval, cohen_kappa,
    kappa_interval, leak_ids, kind_mix, total_variation, confusion_by_segment,
    as_indicator, sensitivity_flip, build_card, admit_decide, ReportCard,
)


def test_rogan_gladen_recovers_known_prevalence():
    # Se=0.80, Sp=0.98, p=0.05 -> p_obs = 0.80*0.05 + 0.02*0.95 = 0.059
    rec = rogan_gladen(0.059, 0.80, 0.98)
    assert abs(rec["p"] - 0.05) < 1e-12
    try:
        rogan_gladen(0.5, 0.4, 0.4)
        assert False, "should refuse Youden <= 0"
    except ValueError:
        pass


def test_ppi_corrects_a_constant_bias():
    # Gold rate 0.20; judge under-calls by 0.05 on both labelled and unlabelled.
    y = [1, 1, 0, 0, 0, 0, 1, 0, 0, 0]  # 3/10 = 0.30
    f_n = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0]  # 2/10 = 0.20
    f_N = [1, 0, 0, 0] * 25  # 25/100 = 0.25
    est = ppi(y, f_n, f_N)
    assert abs(est["rectifier"] - 0.10) < 1e-12
    assert abs(est["p"] - 0.35) < 1e-12  # 0.30 + (0.25 - 0.20)
    # If the judge matches gold on the labelled set, PPI equals the large-set rate.
    f_match = list(y)
    est2 = ppi(y, f_match, f_N)
    assert abs(est2["p"] - 0.25) < 1e-12


def test_ppi_interval_contains_the_point():
    y = [1, 0, 0, 1, 0, 0, 0, 0, 1, 0]
    f = [1, 0, 0, 0, 0, 0, 0, 0, 1, 0]
    f_N = [0] * 80 + [1] * 20
    iv = ppi_interval(y, f, f_N)
    assert iv["ci"][0] < iv["p"] < iv["ci"][1]
    assert iv["n"] == 10 and iv["N"] == 100


def test_kappa_and_bootstrap_interval():
    truth = ["fail"] * 8 + ["pass"] * 32
    pred = ["fail"] * 7 + ["pass"] + ["fail"] + ["pass"] * 31  # TP=7 FN=1 FP=1 TN=31
    k = cohen_kappa(truth, pred)
    assert 0.7 < k < 0.95
    iv = kappa_interval(truth, pred, n_boot=500, seed=2026)
    assert iv["ci"][0] <= iv["kappa"] <= iv["ci"][1]


def test_leak_and_kind_mix():
    assert leak_ids(["t-1", "t-2", "t-3"], ["t-2", "t-9"]) == ["t-2"]
    assert leak_ids(["t-1"], ["t-2"]) == []
    a = kind_mix(["right_no"] * 80 + ["fail_amount"] * 20)
    b = kind_mix(["right_no"] * 80 + ["fail_amount"] * 20)
    c = kind_mix(["right_no"] * 20 + ["fail_amount"] * 80)
    assert total_variation(a, b) == 0.0
    assert abs(total_variation(a, c) - 0.60) < 1e-12


def test_segment_confusion_and_sensitivity_move():
    segments = ["en"] * 6 + ["es"] * 4
    truth = ["fail", "fail", "pass", "pass", "pass", "pass",
             "fail", "pass", "pass", "pass"]
    pred = ["fail", "pass", "pass", "pass", "pass", "pass",
            "pass", "pass", "pass", "fail"]
    tab = confusion_by_segment(segments, truth, pred)
    assert tab["en"]["tp"] == 1 and tab["en"]["fn"] == 1 and tab["en"]["n"] == 6
    assert tab["es"]["fn"] == 1 and tab["es"]["fp"] == 1
    assert tab["_max_gap"] == tab["_max_gap"]
    y = as_indicator(truth)
    f = as_indicator(pred)
    f_N = [0.0] * 90 + [1.0] * 10
    sens = sensitivity_flip(y, f, f_N, n_flip=3, seed=2026)
    assert sens["n_flip"] == 3
    assert sens["moved"] != 0


def test_admit_decide_refuses_a_lookalike_and_accepts_a_clean_card():
    truth = ["fail"] * 10 + ["pass"] * 190
    pred = ["fail"] * 8 + ["pass"] * 2 + ["fail"] * 1 + ["pass"] * 189
    unlabeled = ["fail"] * 26 + ["pass"] * 2374
    segments = ["en"] * 170 + ["es"] * 30
    card = build_card(
        truth, pred, unlabeled,
        judge="fee-judge-v1", metric_card="MC-02 v1.1",
        segments=segments,
        val_ids=[f"t-{i}" for i in range(200)],
        reserved_ids=[f"dev-{i}" for i in range(100)],
        val_kinds=["right_no"] * 170 + ["fail_amount"] * 30,
        reserved_kinds=["right_no"] * 70 + ["fail_amount"] * 30,  # TV = 0.15
        invariance_key=["short"] * 100 + ["long"] * 100,
        n_boot=200, seed=2026,
    )
    decision = admit_decide(card)
    assert decision["admit"] is True
    assert decision["role"] == "decide"
    # A cloned reserved mix must refuse.
    card2 = build_card(
        truth, pred, unlabeled,
        judge="fee-judge-v1", metric_card="MC-02 v1.1",
        val_ids=["t-1"], reserved_ids=["t-1"],
        val_kinds=["right_no"] * 80 + ["fail_amount"] * 20,
        reserved_kinds=["right_no"] * 80 + ["fail_amount"] * 20,
        n_boot=50, seed=2026,
    )
    decision2 = admit_decide(card2)
    assert decision2["admit"] is False
    assert any("overlaps reserved" in r or "kind-mix" in r for r in decision2["reasons"])
