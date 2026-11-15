"""Ch47 lab: incident-to-eval pipeline + release ritual cards. Offline SIM."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def incident_coverage(fix: dict) -> dict:
    sample = {r["trace_id"] for r in fix["rows"]}
    cards = []
    for inc in fix["incidents"]:
        tid = inc["linked_trace_id"]
        covered = tid in sample
        cards.append({
            "incident_id": inc["incident_id"],
            "linked_trace_id": tid,
            "in_weekly_sample": covered,
            "force_include_required": not covered,
            "progression_set": inc.get("progression_set", False),
        })
    missed = [c for c in cards if not c["in_weekly_sample"]]
    return {
        "n_incidents": len(cards),
        "n_missed": len(missed),
        "cards": cards,
        "pipeline_open": len(missed) > 0,
    }


def eval_registry() -> list[dict]:
    """Teaching eval registry rows — owners and gates (EDDOps-shaped)."""
    return [
        {"eval_id": "hardship-wrong-offer", "owner": "Victor", "gate": "release", "target": "Wilson hi < 0.5%", "retest": "model|prompt|policy|incident"},
        {"eval_id": "fee-wrong-explanation", "owner": "Victor", "gate": "release", "target": "Wilson hi < 2%", "retest": "model|prompt|policy|incident"},
        {"eval_id": "annotation-agreement", "owner": "Grace", "gate": "monitor", "target": "kappa inform", "retest": "quarterly"},
        {"eval_id": "incident-seed-coverage", "owner": "EvalLead", "gate": "release", "target": "0 missed linked traces", "retest": "each_incident"},
    ]


def release_ritual(coverage: dict) -> dict:
    """Ship verb blocked while incident coverage pipeline_open."""
    return {
        "candidate": "rc-ch47-teaching",
        "gates_checked": ["hardship-wrong-offer", "fee-wrong-explanation", "incident-seed-coverage"],
        "incident_seed_coverage_MEETS": coverage["n_missed"] == 0,
        "ship_verb": "HOLD" if coverage["n_missed"] else "SHIP_CANDIDATE",
        "victor_100pct_signature": "PENDING_after_gates",  # teaching: signs only after gates + monitoring plan
        "SIMULATED": True,
        "live_ab": "PENDING",
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    cov = incident_coverage(fix)
    reg = eval_registry()
    ritual = release_ritual(cov)
    evidence = {
        "control_objective": "every linked incident trace is in an eval set before release; 100% traffic only after Victor signs with gates MEETS or residual-risk note",
        "digest": fix["digest"],
        "seed": fix["seed"],
        "n_week": fix["n_week"],
        "coverage": cov,
        "registry": reg,
        "ritual": ritual,
        "traffic_share_teaching": fix["traffic_share_teaching"],
        "prior_traffic_share": fix["prior_traffic_share"],
        "SIMULATED": True,
        "live_provider_eval_sweeps": "PENDING",
    }
    raw = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    record = {"record_sha12": hashlib.sha256(raw).hexdigest()[:12], "experiment_id": "ch47-eval-first-company"}
    payload = {"SIMULATED": True, "evidence_pack": evidence, "record": record, "digest": fix["digest"]}
    (OUT / "lab.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"digest": fix["digest"], "record": record["record_sha12"], "n_missed": cov["n_missed"], "ship": ritual["ship_verb"]}, indent=2))


if __name__ == "__main__":
    main()
