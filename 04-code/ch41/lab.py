"""Chapter 41 lab: cost of knowing — deterministic, no paid API."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.costknow import (
    KIND_INVOICE,
    KIND_RESERVE,
    KIND_HEADROOM,
    KIND_SIM,
    KIND_TOKEN,
    classify_line,
    study_ceiling,
    amortise_study,
    release_bill,
    waterfall,
    cheap_first_cascade,
    sample_by_risk,
    bias_battery_gate,
    cost_per_decision,
)

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    c16 = fix["ch16"]
    ceil = study_ceiling(c16["charged_usd"], c16["unreconciled_usd"], c16["headroom_usd"])
    assert abs(ceil["safe_ceiling_usd"] - c16["safe_ceiling_usd"]) < 1e-9

    lines = [
        classify_line(
            amount_usd=c16["charged_usd"],
            kind=KIND_INVOICE,
            unit="USD study total (ledger committed)",
            as_of="2026-11-08",
            source=c16["run_id"],
        ),
        classify_line(
            amount_usd=c16["unreconciled_usd"],
            kind=KIND_RESERVE,
            unit="USD worst-case unreconciled hung-judge reserves",
            as_of="2026-11-08",
            source=c16["run_id"] + "/budget_ledger",
        ),
        classify_line(
            amount_usd=c16["headroom_usd"],
            kind=KIND_HEADROOM,
            unit="USD safety headroom (not a charge)",
            as_of="2026-11-08",
            source="budget policy",
        ),
        classify_line(
            amount_usd=c16["small_judge_per_call_usd"],
            kind=KIND_TOKEN,
            unit="USD per judge call (token-priced at study list prices)",
            as_of=c16["prices_usd_per_mtok_as_of"],
            source="lab.json models.small.per_call",
        ),
    ]

    wf = waterfall(fix["waterfall"])
    assert abs(wf["start_usd"] - 1900.0) < 1e-9
    assert abs(wf["end_usd"] - 640.0) < 1e-9

    cascade = cheap_first_cascade(fix["cascade_volumes"], fix["cascade_unit_costs"])
    risk = sample_by_risk(fix["strata"])
    inj = fix["inject"]
    gate_fail = bias_battery_gate(
        tpr=inj["cheap_tpr"],
        tnr=inj["cheap_tnr"],
        position_flip_rate=inj["position_flip_rate"],
    )
    gate_ok = bias_battery_gate(
        tpr=0.98,
        tnr=0.993,
        position_flip_rate=inj["baseline_flip_rate"],
    )
    assert gate_fail["admit"] is False and gate_fail["failed_bias_battery"] is True
    assert gate_ok["admit"] is True

    amort = amortise_study(c16["charged_usd"], n_releases_benefiting=12)
    # SIM release bill at end of waterfall
    end_bill = release_bill(call_usd=40.0, ordered_read_usd=520.0, ci_usd=60.0, other_usd=20.0)
    assert abs(end_bill["total_usd"] - 640.0) < 1e-9
    cpd = cost_per_decision(end_bill["total_usd"], n_decisions=80)

    # five-step cuts (baseline + 5 cuts = 6 waterfall rows)
    teaching = {
        "release_1900_to_640": wf["start_usd"] == 1900.0 and wf["end_usd"] == 640.0,
        "five_cuts": len(wf["steps"]) == 6,
        "saved_usd": wf["saved_usd"],
        "cheap_fails_bias": gate_fail["failed_bias_battery"],
        "baseline_admits": gate_ok["admit"],
        "ch16_ceiling_match": abs(ceil["safe_ceiling_usd"] - 6.291941) < 1e-6,
        "rows_not_requests": c16["jsonl_rows"] != c16["request_ids"],
        "order_not_decide": c16["order_not_decide"],
    }

    out = {
        "seed": fix["seed"],
        "digest": fix["digest"],
        "simulated": True,
        "ch16_verified": c16,
        "study_ceiling": ceil,
        "cost_lines": lines,
        "waterfall": wf,
        "cascade": cascade,
        "risk_sample": risk,
        "inject_gate": gate_fail,
        "baseline_gate": gate_ok,
        "amortisation": amort,
        "end_release_bill": end_bill,
        "cost_per_decision": cpd,
        "teaching": teaching,
        "label": "SIMULATED release waterfall; Ch16 study costs are verified ledger figures",
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"digest": out["digest"], "saved": wf["saved_usd"], "teaching": teaching}, indent=2))


if __name__ == "__main__":
    main()
