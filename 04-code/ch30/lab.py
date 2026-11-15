from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.gateway import migration_delta, release_decision, silent_change_score, deprecation_plan, judge_revalidation_triggers, pin_record

OUT = Path(__file__).parent / "out"

def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    rows = fix["rows"]
    n = len(rows)
    b = {
        "hardship_ok": sum(r["baseline"]["hardship_ok"] for r in rows) / n,
        "fee_ok": sum(r["baseline"]["fee_ok"] for r in rows) / n,
        "latency_ms": sum(r["baseline"]["latency_ms"] for r in rows) / n,
    }
    c = {
        "hardship_ok": sum(r["candidate"]["hardship_ok"] for r in rows) / n,
        "fee_ok": sum(r["candidate"]["fee_ok"] for r in rows) / n,
        "latency_ms": sum(r["candidate"]["latency_ms"] for r in rows) / n,
    }
    delta = migration_delta(b, c)
    # HOLD if latency regresses (higher ms) — treat latency as lower-is-better by flipping sign in decision helper
    rows_for_dec = []
    for r in delta["rows"]:
        rr = dict(r)
        if r["metric"] == "latency_ms":
            rr["delta"] = r["baseline"] - r["candidate"]  # positive if improved (faster)
        rows_for_dec.append(rr)
    # Actually release_decision holds on delta<0; for latency we want hold when candidate slower (candidate>baseline)
    # So encode latency delta as baseline-candidate (negative when slower)
    dec = release_decision(rows_for_dec, hold_on_any_regression=True)
    silent = silent_change_score(fix["canary_repeats"])
    plan = deprecation_plan(fix["deprecation_notice_days"], suite_ready=True, migration_hold=(dec["decision"]=="HOLD"))
    triggers = judge_revalidation_triggers(True, False, False, silent["flip_rate"])
    out = {
        "seed": fix["seed"],
        "digest": fix["digest"],
        "simulated": True,
        "pins": [
            pin_record(fix["baseline_model"], "harbor-gateway", "2028-06-01", fix["digest"]+"-b"),
            pin_record(fix["candidate_model"], "harbor-gateway", "2028-09-01", fix["digest"]+"-c"),
        ],
        "baseline_rates": b,
        "candidate_rates": c,
        "delta": delta,
        "decision": dec,
        "silent_canary": silent,
        "deprecation": plan,
        "judge_triggers": triggers,
        "touchpoint": "deprecation migration; two metrics improve, latency regresses; HOLD",
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in out if k != "delta"}, indent=2)[:2000])
    print("delta rows", delta["rows"])
    print("decision", dec)

if __name__ == "__main__":
    main()
