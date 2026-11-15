from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.weeklyreport import (
    metric_card,
    hierarchy_page,
    trend_point,
    hides_segment_regression,
    render_one_page,
    slice_gate_row,
    overall_delta,
    segment_delta,
)

OUT = Path(__file__).parent / "out"

# Governing hardship weekly-monitor policy (MC-03 / escalate_to_decide).
# Upstream: ledger Ch15 decision table — monitors MC-03 "weekly rate above 1%".
# Same target must drive hierarchy metric_card AND slice_gate_row views.
HARDSHIP_MONITOR_TARGET = 0.01


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    series = []
    for week, of, on, hf, hn, ff, fn in fix["weeks"]:
        series.append(
            trend_point(
                week,
                overall_failures=of,
                overall_n=on,
                segments={
                    "hardship": {"failures": hf, "n": hn},
                    "fee": {"failures": ff, "n": fn},
                },
            )
        )
    hide = hides_segment_regression(
        series,
        segment=fix["segment_name"],
        overall_ok_if_delta_le=fix["overall_ok_if_delta_le"],
        segment_bad_if_delta_ge=fix["segment_bad_if_delta_ge"],
    )
    d = fix["decide"]
    g = fix["gate_fee"]
    cards = [
        metric_card(
            d["name"],
            tier="decide",
            failures=d["failures"],
            n=d["n"],
            owner="Victor",
            action="hold_widen_until_bound",
            target=d["target"],
        ),
        metric_card(
            g["name"],
            tier="gate",
            failures=g["failures"],
            n=g["n"],
            owner="Ryan",
            action="replay_fee_set",
            target=g["target"],
        ),
        metric_card(
            "fee_slice_monitor",
            tier="monitor",
            failures=series[-1]["segments"]["fee"]["failures"],
            n=series[-1]["segments"]["fee"]["n"],
            owner="eval-lead",
            action="read_if_flag",
            target=0.03,
        ),
        metric_card(
            "hardship_slice_monitor",
            tier="monitor",
            failures=series[-1]["segments"]["hardship"]["failures"],
            n=series[-1]["segments"]["hardship"]["n"],
            owner="eval-lead",
            action="escalate_to_decide",
            target=HARDSHIP_MONITOR_TARGET,
        ),
    ]
    # inform as a non-rate card via hierarchy note — use rate 0/1 placeholder? Better: store separately
    hier = hierarchy_page(cards)
    slices = [
        slice_gate_row("hardship", failures=d["failures"], n=d["n"], gate=d["target"]),
        slice_gate_row("fee", failures=g["failures"], n=g["n"], gate=g["target"]),
        slice_gate_row(
            "hardship_weekly_monitor",
            failures=series[-1]["segments"]["hardship"]["failures"],
            n=series[-1]["segments"]["hardship"]["n"],
            gate=HARDSHIP_MONITOR_TARGET,
        ),
    ]
    headline = (
        "Overall monitor flat; hardship segment regression hidden until slice lines are read."
        if hide["hidden"]
        else "No hidden segment regression under the teaching thresholds."
    )
    what_changed = [
        f"Overall delta {hide['overall_delta']:+.4f} (failures/n first→last).",
        f"Hardship delta {hide['segment_delta']:+.4f}.",
        f"Hidden-regression flag: {hide['hidden']}.",
        f"Ch39 packet: median TTE {fix['packet']['median_tte_days']}d; complaints "
        f"{fix['packet']['complaints_prev_month']}→{fix['packet']['complaints_this_month']}.",
    ]
    ask = [
        "Victor: hold traffic widen on hardship until decide-tier Wilson upper bound is under 0.5%.",
        "Ryan: keep fee gate replay; do not celebrate overall flatness alone.",
        "Rachel: read the one-pager; ad-hoc number requests route to this page first.",
    ]
    page = render_one_page(
        title="Compass Weekly Quality Report",
        week_ending=fix["scoreboard_date"],
        hierarchy=hier,
        headline=headline,
        what_changed=what_changed,
        ask=ask,
        packet={
            "median_tte_days": fix["packet"]["median_tte_days"],
            "n_incidents_closed_to_eval": fix["packet"]["n_incidents_closed_to_eval"],
            "complaints_this_month": fix["packet"]["complaints_this_month"],
            "complaints_prev_month": fix["packet"]["complaints_prev_month"],
            "inctoeval_digest": fix["packet"]["inctoeval_digest"],
        },
    )
    (OUT / "weekly_page.txt").write_text(page)
    out = {
        "seed": fix["seed"],
        "digest": fix["digest"],
        "simulated": True,
        "label": "SIMULATED",
        "n_weeks": len(series),
        "series": series,
        "hide": hide,
        "overall_delta": overall_delta(series),
        "hardship_delta": segment_delta(series, "hardship"),
        "fee_delta": segment_delta(series, "fee"),
        "hierarchy": hier,
        "slices": slices,
        "decide_card": cards[0],
        "gate_card": cards[1],
        "page_path": "out/weekly_page.txt",
        "page_chars": len(page),
        "packet": fix["packet"],
        "scoreboard_date": fix["scoreboard_date"],
        "hardship_monitor_target": HARDSHIP_MONITOR_TARGET,
        "teaching": {
            "hidden_segment_regression": hide["hidden"],
            "overall_flat_or_better": hide["overall_looks_ok"],
            "hardship_regressed": hide["segment_regressed"],
            "eight_weeks": len(series) == 8,
            "page_rendered": len(page) > 200,
        },
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("digest", "hide", "teaching", "overall_delta", "hardship_delta")}, indent=2))


if __name__ == "__main__":
    main()
