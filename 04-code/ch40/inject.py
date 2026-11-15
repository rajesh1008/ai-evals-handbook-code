"""Failure injection: overall trend hides hardship regression (Chapter 40)."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.weeklyreport import trend_point, hides_segment_regression

OUT = Path(__file__).parent / "out"


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
    # Blind overall-only reader would see:
    overall_rates = [p["overall"]["rate"] for p in series]
    blind_ok = overall_rates[-1] <= overall_rates[0]
    hid = hides_segment_regression(
        series,
        segment="hardship",
        overall_ok_if_delta_le=0.0,
        segment_bad_if_delta_ge=0.01,
    )
    caught = hid["hidden"] and blind_ok
    out = {
        "injection": "trend_hides_segment_regression",
        "blind_overall_ok": blind_ok,
        "detector_hidden_flag": hid["hidden"],
        "caught": caught,
        "overall_rates": overall_rates,
        "hardship_rates": [p["segments"]["hardship"]["rate"] for p in series],
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
