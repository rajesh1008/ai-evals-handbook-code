"""Ch51 lab: Truss-shaped eval for Toronto case; SIMULATED."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def offline_suite(traces: list[dict], taxonomy: list[str]) -> dict:
    """Offline cards that never slice by billing-cycle day — the failure mode."""
    n = len(traces)
    fails = sum(1 for t in traces if t["offline_label"] == "fail")
    return {
        "n": n,
        "pass_rate": round(1 - fails / n, 4),
        "taxonomy_used": taxonomy,
        "sliced_by_cycle_day": False,
        "BillingCycleEdge_card": False,
        "SIMULATED": True,
    }


def online_cycle_day(traces: list[dict]) -> dict:
    edge = [t for t in traces if t["day_in_cycle"] == 1 and t["midcycle_change"]]
    complaints = sum(1 for t in edge if t.get("online_complaint"))
    all_cycle1 = [t for t in traces if t["day_in_cycle"] == 1]
    return {
        "cycle_day_1_n": len(all_cycle1),
        "cycle_day_1_midcycle_n": len(edge),
        "complaints": complaints,
        "complaint_rate": round(complaints / max(len(all_cycle1), 1), 4),
        "complaint_pp_vs_offline_expectation": round(100 * complaints / max(len(all_cycle1), 1), 1),
        "root_cause": "offline_taxonomy_missing_BillingCycleEdge",
        "SIMULATED": True,
    }


def harbor_compare(cases: dict, borrow: list) -> dict:
    return {
        "rows": [
            {
                "case": k,
                "decide_owner": v.get("decide_owner"),
                "decide_metric": v.get("decide_metric"),
                "failed_practice": v.get("failed_practice", False),
            }
            for k, v in cases.items()
        ],
        "borrow_count": len(borrow),
        "SIMULATED": True,
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    tax = fix["cases"]["toronto"]["taxonomy_offline"]
    off = offline_suite(fix["telecom_traces"], tax)
    on = online_cycle_day(fix["telecom_traces"])
    cmp_ = harbor_compare(fix["cases"], fix["harbor_borrow"])
    evidence = {
        "control_objective": "replay Toronto offline/online mismatch; compare four teaching cases; preserve Ch16 kinds",
        "seed": fix["seed"],
        "digest": fix["digest"],
        "offline": off,
        "online": on,
        "harbor_compare": cmp_,
        "CH16": fix["CH16"],
        "SIMULATED": True,
        "live_provider_sweeps": "PENDING",
        "teaching_scenarios": True,
    }
    blob = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    record = hashlib.sha256(blob).hexdigest()
    out = {
        "digest": fix["digest"],
        "record": {"record_sha256": record, "record_sha12": record[:12]},
        "evidence_pack": evidence,
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2) + "\n")
    print("lab record", record[:12], "offline_pass", off["pass_rate"], "online_edge_complaints", on["complaints"])


if __name__ == "__main__":
    main()
