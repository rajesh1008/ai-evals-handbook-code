"""Ch53 lab: SIMULATED two-gen-newer gates; trajectory catch / outcome miss."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    assert fix["SIMULATED"] is True
    assert fix["live_provider_comparison"] == "PENDING"
    gates = {g["model_id"]: g for g in fix["gates"]}
    bas = gates["sim_gen_N"]
    new = gates["sim_gen_N_plus_2"]
    assert bas["inject_caught_trajectory"] and bas["inject_missed_by_outcome"]
    assert new["inject_caught_trajectory"] and new["inject_missed_by_outcome"]
    # Harbor last look inherited
    hl = fix["harbor_last_look"]
    assert hl["hardship_status"] == "OPEN"
    assert hl["fee_status"] == "OPEN"
    assert hl["rachel_share"] == "CONDITIONAL_10pct"
    assert hl["sarah_kinds"] == "MEETS_KINDS"
    assert hl["ch52_digest"] == "73ee6bb8ebe5"
    assert abs(fix["CH16"]["ceiling_sum_usd"] - 6.291941) < 1e-9

    evidence = {
        "control_objective": fix["control_objective"],
        "seed": fix["seed"],
        "digest": fix["digest"],
        "SIMULATED": True,
        "live_provider_comparison": "PENDING",
        "no_paid_calls": True,
        "models": fix["models"],
        "gates": fix["gates"],
        "inject_primary": fix["inject_primary"],
        "inject_case": fix["inject_case"],
        "inject_caught": True,
        "harbor_last_look": hl,
        "CH16": fix["CH16"],
        "delta_outcome_pass": round(new["outcome_pass_rate"] - bas["outcome_pass_rate"], 4),
        "note": "All model scores are deterministic SIMULATED fixtures, not live provider results",
    }
    blob = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    record = hashlib.sha256(blob).hexdigest()
    out = {
        "digest": fix["digest"],
        "record": {"record_sha256": record, "record_sha12": record[:12]},
        "evidence_pack": evidence,
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2) + "\n")
    lines = [
        f"Ch53 lab SIMULATED seed={fix['seed']} digest={fix['digest']} record={record[:12]}",
        f"inject {fix['inject_primary']} on {fix['inject_case']} caught_by_trajectory=True missed_by_outcome=True",
        f"baseline outcome_pass={bas['outcome_pass_rate']} traj_pass={bas['trajectory_pass_rate']}",
        f"two_gen_newer outcome_pass={new['outcome_pass_rate']} traj_pass={new['trajectory_pass_rate']}",
        f"harbor last look OPEN hardship+fee CONDITIONAL_10pct MEETS_KINDS ceiling={fix['CH16']['ceiling_sum_usd']}",
        "live_provider_comparison=PENDING no_paid_calls=True",
    ]
    (OUT / "OUTPUT.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
