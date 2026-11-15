from truss.weeklyreport import (
    metric_card,
    hierarchy_page,
    trend_point,
    hides_segment_regression,
    render_one_page,
    slice_gate_row,
    overall_delta,
)


def test_metric_card_wilson_and_target():
    c = metric_card(
        "wrong_hardship_offer",
        tier="decide",
        failures=1,
        n=400,
        owner="Victor",
        action="hold_widen",
        target=0.005,
    )
    assert c["rate"] == 1 / 400
    assert c["wilson_lo"] < c["rate"] < c["wilson_hi"]
    assert c["meets_target"] is False  # upper bound not under 0.5%


def test_hierarchy_order():
    cards = [
        metric_card("a", tier="inform", failures=0, n=10, owner="Rachel", action="read"),
        metric_card("b", tier="decide", failures=0, n=100, owner="Victor", action="gate", target=0.01),
    ]
    h = hierarchy_page(cards)
    assert h["tiers"][0] == "decide"
    assert len(h["by_tier"]["decide"]) == 1
    assert len(h["by_tier"]["inform"]) == 1


def test_hides_segment_regression():
    weeks = []
    # overall flat 4/1000; hardship rises 1/200 -> 4/200
    for i, (hf, hn) in enumerate([(1, 200), (1, 200), (2, 200), (4, 200)]):
        of, on = 4, 1000
        weeks.append(
            trend_point(
                f"W{i}",
                overall_failures=of,
                overall_n=on,
                segments={"hardship": {"failures": hf, "n": hn}},
            )
        )
    hid = hides_segment_regression(weeks, segment="hardship")
    assert hid["overall_looks_ok"] is True
    assert hid["segment_regressed"] is True
    assert hid["hidden"] is True
    assert overall_delta(weeks) == 0.0


def test_render_contains_hierarchy_and_packet():
    cards = [
        metric_card(
            "wrong_hardship_offer",
            tier="decide",
            failures=1,
            n=400,
            owner="Victor",
            action="hold",
            target=0.005,
        )
    ]
    page = render_one_page(
        title="Compass Weekly Quality",
        week_ending="2029-05-28",
        hierarchy=hierarchy_page(cards),
        headline="Hardship slice open; overall flat.",
        what_changed=["Hardship Wilson upper bound crossed 0.5% target."],
        ask=["Hold traffic widen until hardship bound recovers."],
        packet={"median_tte_days": 4, "complaints_this_month": 31},
    )
    assert "METRIC HIERARCHY" in page
    assert "INCIDENT→EVAL PACKET" in page
    assert "median_tte_days: 4" in page


def test_slice_gate():
    row = slice_gate_row("hardship", failures=0, n=600, gate=0.01)
    assert row["holds"] is True
    row2 = slice_gate_row("hardship", failures=10, n=200, gate=0.01)
    assert row2["holds"] is False


def test_bad_tier_rejected():
    try:
        metric_card("x", tier="dashboard", failures=0, n=1, owner="a", action="b")
        assert False
    except ValueError:
        pass


def test_hardship_monitor_policy_single_target_from_lab():
    """Ch40: hierarchy monitor card and slice view must share one policy target.

    Upstream authority: ledger Ch15 MC-03 "weekly rate above 1%" + lab
    HARDSHIP_MONITOR_TARGET. A deliberate clash (0.01 vs 0.02) must fail.
    """
    from pathlib import Path
    import json
    import importlib.util

    root = Path(__file__).resolve().parents[3]  # ai-evals-book
    lab_path = root / "04-code" / "ch40" / "out" / "lab.json"
    assert lab_path.exists(), "run 04-code/ch40/run_all.sh before suite"
    lab = json.loads(lab_path.read_text())
    mon = [
        c
        for c in lab["hierarchy"]["by_tier"]["monitor"]
        if c["name"] == "hardship_slice_monitor"
    ][0]
    sl = [s for s in lab["slices"] if s["slice"] == "hardship_weekly_monitor"][0]
    # Governing policy
    assert lab.get("hardship_monitor_target") == 0.01
    assert mon["target"] == 0.01
    assert sl["gate"] == 0.01
    assert mon["target"] == sl["gate"] == lab["hardship_monitor_target"]
    # Decision colour still OPEN/BREAKS on teaching rates (raw 5/200)
    assert mon["meets_target"] is False
    assert sl["holds"] is False
    # Detect deliberate clash pattern the chapter forbids
    deliberate_clash = {"hierarchy_target": 0.01, "slice_gate": 0.02}
    assert deliberate_clash["hierarchy_target"] != deliberate_clash["slice_gate"]
    # Production views must NOT look like that clash
    assert not (mon["target"] == 0.01 and sl["gate"] == 0.02)


def test_slice_gate_matches_metric_card_when_same_policy():
    """Same failures/n + same policy => slice.holds == card.meets_target."""
    failures, n, target = 5, 200, 0.01
    card = metric_card(
        "hardship_slice_monitor",
        tier="monitor",
        failures=failures,
        n=n,
        owner="eval-lead",
        action="escalate_to_decide",
        target=target,
    )
    row = slice_gate_row("hardship_weekly_monitor", failures=failures, n=n, gate=target)
    assert card["meets_target"] is False
    assert row["holds"] is False
    assert abs(card["wilson_hi"] - row["wilson_hi"]) < 1e-12
