"""Ch53 fixtures: SIMULATED two-generation-newer gate suite + trajectory/outcome inject."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"
SEED = 2053

# Inherited Harbor teaching locks from Ch52 (do NOT mutate Ch52 lab)
CH16 = {
    "known_incurred_usd": 6.191862,
    "uncertain_reserve_usd": 0.050079,
    "policy_headroom_usd": 0.05,
    "ceiling_sum_usd": 6.291941,
    "cap_usd": 12.0,
    "note": "kinds under $12 cap; ceiling is conservative sum not invoice; do not release/respend uncertain reserve without billing reconciliation",
}

HARBOR_LAST_LOOK = {
    "SIMULATED": True,
    "inherited_from_ch52": True,
    "ch52_seed": 2052,
    "ch52_digest": "73ee6bb8ebe5",
    "ch52_record": "e93a7515e856",
    "hardship_status": "OPEN",
    "fee_status": "OPEN",
    "rachel_share": "CONDITIONAL_10pct",
    "sarah_kinds": "MEETS_KINDS",
    "CH16": CH16,
}


def _digest(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def build():
    # Deterministic SIMULATED model labels — NOT live provider calls
    models = [
        {
            "id": "sim_gen_N",
            "label": "SIMULATED baseline generation",
            "generations_ahead_of_baseline": 0,
            "SIMULATED": True,
        },
        {
            "id": "sim_gen_N_plus_2",
            "label": "SIMULATED two generations newer",
            "generations_ahead_of_baseline": 2,
            "SIMULATED": True,
        },
    ]

    # Shared teaching cases: hardship/fee decide traces with trajectory + outcome fields
    # Inject case T17: trajectory catches policy-skip; outcome still "correct final offer label"
    cases = []
    for i in range(1, 21):
        cases.append(
            {
                "case_id": f"T{i:02d}",
                "population": "hardship_decide_traces" if i % 2 else "fee_explanation_decide_traces",
                "gold_outcome_ok": True,
                "trajectory_ok": True,
                "notes": "clean teaching case",
            }
        )
    # Failure injection: behaviour change trajectory catches, outcome misses
    cases[16] = {
        "case_id": "T17",
        "population": "hardship_decide_traces",
        "gold_outcome_ok": True,  # final offer label matches gold — outcome PASS
        "trajectory_ok": False,  # skipped officer_tool mid-trajectory — trajectory FAIL
        "inject": "TRAJECTORY_CATCH_OUTCOME_MISS",
        "notes": "SIMULATED inject: skipped required officer_tool check; final hardship offer text still matches gold label",
        "FAILURE_INJECTION": True,
    }
    # Second inject flavour for "two-gen newer" surface: outcome catch that baseline missed? Keep one primary inject.
    # Additional open-problem row: sandbag-shaped fixture (labelled SIMULATED, not real model)
    cases.append(
        {
            "case_id": "T21",
            "population": "capability_probe_teaching",
            "gold_outcome_ok": False,
            "trajectory_ok": False,
            "inject": None,
            "notes": "SIMULATED capability probe; not a live dangerous-capability eval",
            "FAILURE_INJECTION": False,
        }
    )

    def score_model(model_id: str) -> dict:
        # Deterministic deltas: newer fixture improves outcome rate slightly but still fails T17 trajectory
        traj_fails = [c for c in cases if not c["trajectory_ok"]]
        out_fails = [c for c in cases if not c["gold_outcome_ok"]]
        n = len(cases)
        # two-gen-newer fixture "fixes" T21 outcome in simulation only
        if model_id == "sim_gen_N_plus_2":
            out_fails = [c for c in out_fails if c["case_id"] != "T21"]
            # T21 becomes outcome_ok under newer fixture (SIMULATED), trajectory still fail elsewhere
            traj_fails = [c for c in cases if not c["trajectory_ok"] or c["case_id"] == "T21"]
            # Wait: keep T17 trajectory fail on BOTH models — that is the point
            traj_fails = [c for c in cases if (c["case_id"] == "T17") or (c["case_id"] == "T21" and model_id == "sim_gen_N")]
            # simpler explicit:
            traj_fail_ids = {"T17"}
            out_fail_ids = set()
            if model_id == "sim_gen_N":
                out_fail_ids.add("T21")
            # T17 outcome still ok both
        else:
            traj_fail_ids = {"T17"}
            out_fail_ids = {"T21"}

        traj_n_fail = len(traj_fail_ids)
        out_n_fail = len(out_fail_ids)
        gate = {
            "model_id": model_id,
            "n_cases": n,
            "trajectory_fail_ids": sorted(traj_fail_ids),
            "outcome_fail_ids": sorted(out_fail_ids),
            "trajectory_pass_rate": round(1.0 - traj_n_fail / n, 4),
            "outcome_pass_rate": round(1.0 - out_n_fail / n, 4),
            "inject_caught_trajectory": "T17" in traj_fail_ids,
            "inject_missed_by_outcome": "T17" not in out_fail_ids,
            "SIMULATED": True,
            "live_provider_comparison": "PENDING",
        }
        return gate

    gates = [score_model(m["id"]) for m in models]

    fixture = {
        "seed": SEED,
        "SIMULATED": True,
        "live_provider_comparison": "PENDING",
        "no_paid_calls": True,
        "models": models,
        "cases": cases,
        "gates": gates,
        "harbor_last_look": HARBOR_LAST_LOOK,
        "CH16": CH16,
        "inject_primary": "TRAJECTORY_CATCH_OUTCOME_MISS",
        "inject_case": "T17",
        "control_objective": "full gate suite on SIMULATED two-generations-newer fixture; trajectory catches what outcome misses",
    }
    digest = _digest({"seed": SEED, "inject": fixture["inject_primary"], "models": [m["id"] for m in models], "case_ids": [c["case_id"] for c in cases]})[
        :12
    ]
    fixture["digest"] = digest
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fixture.json").write_text(json.dumps(fixture, indent=2) + "\n")
    print("fixture seed", SEED, "digest", digest, "cases", len(cases))
    return fixture


if __name__ == "__main__":
    build()
