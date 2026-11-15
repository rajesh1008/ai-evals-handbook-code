"""Three Try It Yourself variations — Chapter 40."""
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
)

OUT = Path(__file__).parent / "out"


def try1_tighten_target():
    """Same decide counts; tighten target to 0.3% — does MEETS flip?"""
    c_loose = metric_card("who", tier="decide", failures=1, n=500, owner="V", action="a", target=0.01)
    c_tight = metric_card("who", tier="decide", failures=1, n=500, owner="V", action="a", target=0.003)
    return {
        "name": "tighten_target",
        "loose_meets": c_loose["meets_target"],
        "tight_meets": c_tight["meets_target"],
        "wilson_hi": c_tight["wilson_hi"],
    }


def try2_force_visible_segment():
    """If hardship tracked on the page, hidden flag still true but ask changes."""
    fix = json.loads((OUT / "fixture.json").read_text())
    series = []
    for week, of, on, hf, hn, ff, fn in fix["weeks"]:
        series.append(
            trend_point(
                week,
                overall_failures=of,
                overall_n=on,
                segments={"hardship": {"failures": hf, "n": hn}},
            )
        )
    hid = hides_segment_regression(series, segment="hardship", segment_bad_if_delta_ge=0.01)
    return {"name": "force_visible_segment", "hidden": hid["hidden"], "segment_delta": hid["segment_delta"]}


def try3_shorter_page_for_rachel():
    cards = [
        metric_card("wrong_hardship_offer", tier="decide", failures=2, n=420, owner="Victor", action="hold", target=0.005)
    ]
    page = render_one_page(
        title="Compass Weekly (Rachel cut)",
        week_ending="2029-05-28",
        hierarchy=hierarchy_page(cards),
        headline="One decide metric.",
        what_changed=["Hardship decide open."],
        ask=["Hold widen."],
        packet=None,
    )
    return {"name": "shorter_page", "chars": len(page), "has_packet": "INCIDENT→EVAL PACKET" not in page}


def main():
    rows = [try1_tighten_target(), try2_force_visible_segment(), try3_shorter_page_for_rachel()]
    (OUT / "try_its.json").write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
