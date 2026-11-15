"""Aggregate SIMULATED reviewer analytics for Chapter 28."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.reviewer import (
    override_rate, approval_time_summary, per_reviewer_table, automation_bias_rate,
    fatigue_curve, post_review_error_rate, agreement_with_gold, second_review_sample,
)

OUT = Path(__file__).parent / "out"

def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    rows = fix["rows"]
    tab = per_reviewer_table(rows)
    rubber = next(r for r in tab if r["reviewer_id"] == fix["named_rubber"])
    times = [r["approval_seconds"] for r in rows]
    out = {
        "seed": fix["seed"],
        "digest": fix["digest"],
        "simulated": True,
        "n": len(rows),
        "override": override_rate(rows),
        "approval_time": approval_time_summary(times),
        "agreement": agreement_with_gold(rows),
        "per_reviewer": tab,
        "rubber_stamp": rubber,
        "automation_bias": automation_bias_rate(rows),
        "fatigue": fatigue_curve(rows, bins=5),
        "post_review_error": post_review_error_rate(rows),
        "second_review_n": len(second_review_sample(rows, 50)),
        "touchpoint": "post-review error on hardship offers; R-ryan override 0.4% class",
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2))
    print({k: out[k] for k in out if k not in ("per_reviewer", "fatigue")})
    print("rubber", rubber)
    print("post", out["post_review_error"])
    print("bias", out["automation_bias"])

if __name__ == "__main__":
    main()
