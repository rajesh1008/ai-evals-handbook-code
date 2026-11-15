from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.guardmon import (
    promote_check_to_guard,
    evaluate_guard,
    vocabulary_overrefuse,
    latency_breaks_channel,
    sample_production_for_slow_eval,
    timeline_placement,
    hardship_guard_coverage,
    run_guard,
)

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    guards = [
        promote_check_to_guard(c["name"], latency_budget_ms=c["budget_ms"], tier="in_flight")
        for c in fix["checks_to_promote"]
    ]
    preds = [c["pred"] for c in fix["cases"]]
    gold = [c["gold"] for c in fix["cases"]]
    metrics = evaluate_guard(preds, gold)
    vocab = vocabulary_overrefuse(fix["cases"], scary_words=fix["scary_words"])
    lat_ok = latency_breaks_channel(fix["guard_p99_ms_baseline"], channel_timeout_ms=fix["sms_timeout_ms"])
    lat_bad = latency_breaks_channel(fix["guard_p99_ms_injected"], channel_timeout_ms=fix["sms_timeout_ms"])
    sample = sample_production_for_slow_eval(fix["prod_pool"], sample_n=fix["slow_sample_n"], seed=fix["seed"])
    cover = hardship_guard_coverage(fix["hardship_offers"], fix["hardship_guarded"])
    # example in-flight runs
    demo = [
        run_guard(guards[0], signal_pass=True, latency_ms=45),
        run_guard(guards[0], signal_pass=False, latency_ms=50),
        run_guard(guards[1], signal_pass=True, latency_ms=2500),
    ]
    out = {
        "seed": fix["seed"],
        "digest": fix["digest"],
        "simulated": True,
        "guards": guards,
        "metrics": metrics,
        "vocabulary": vocab,
        "latency_baseline": lat_ok,
        "latency_injected": lat_bad,
        "production_sample": {"n": sample["sample_n"], "seed": sample["seed"], "first_ids": sample["ids"][:5]},
        "hardship_coverage": cover,
        "timeline": timeline_placement(),
        "demo_runs": demo,
        "teaching": {
            "two_checks_promoted": len(guards) == 2,
            "hardship_100pct": cover["meets_100pct"],
            "sms_break_caught": lat_bad["breaks_timeout"],
            "over_block_measured": metrics["over_block_rate"] > 0,
        },
        "study_window": fix["study_window"],
        "scoreboard_date": fix["scoreboard_date"],
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("digest", "metrics", "teaching", "hardship_coverage", "latency_injected")}, indent=2))


if __name__ == "__main__":
    main()
