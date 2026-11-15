"""SIMULATED paired upgrade fixture for Chapter 29 (seed 2029)."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2029
N = 200
SLICES = ["fee", "hardship", "payoff", "statement", "lien"]
WEIGHTS = [0.30, 0.25, 0.15, 0.20, 0.10]
SCHEMA_V1 = {
    "get_loan": ["loan_id"],
    "explain_fee": ["loan_id", "fee_code"],
    "check_hardship": ["loan_id", "reason_code"],
    "draft_offer": ["loan_id", "plan_id"],
}
# Silent rename that breaks agents trained on loan_id
SCHEMA_V2_SILENT = {
    "get_loan": ["account_id"],  # renamed
    "explain_fee": ["account_id", "fee_code"],
    "check_hardship": ["loan_id", "reason_code"],
    "draft_offer": ["loan_id", "plan_id"],
}

def main():
    rng = random.Random(SEED)
    cases = []
    for i in range(N):
        cid = f"t-{320101 + i}"
        sl = rng.choices(SLICES, WEIGHTS)[0]
        # baseline A: mostly pass text+tool
        text_a = rng.random() > 0.09  # ~0.91
        tool_a = rng.random() > 0.06  # ~0.94
        # candidate B: slightly better text, worse tools on fee/hardship
        text_b = text_a if rng.random() > 0.15 else (rng.random() > 0.05)
        tool_b = tool_a
        if sl in ("fee", "hardship") and rng.random() < 0.18:
            tool_b = False
            text_b = True  # text still looks fine
        # policy versions for rot: after 3 prompt changes many golds pinned to p1/p2
        policy = rng.choices(["p1", "p2", "p3"], [0.20, 0.25, 0.55])[0]
        gold_matches = policy == "p3"
        # observed tool call under silent schema: agents still emit loan_id
        args_v1 = {"loan_id": f"L-{1000+i}", "fee_code": "LATE"} if sl == "fee" else {"loan_id": f"L-{1000+i}"}
        if sl == "hardship":
            args_v1 = {"loan_id": f"L-{1000+i}", "reason_code": "JOB"}
        tool_name = {"fee": "explain_fee", "hardship": "check_hardship", "payoff": "get_loan",
                     "statement": "get_loan", "lien": "get_loan"}[sl]
        if sl == "hardship" and rng.random() < 0.3:
            tool_name = "draft_offer"
            args_v1 = {"loan_id": f"L-{1000+i}", "plan_id": "H1"}
        cases.append({
            "case_id": cid,
            "slice": sl,
            "baseline": {"text_pass": text_a, "tool_pass": tool_a},
            "candidate": {"text_pass": text_b, "tool_pass": tool_b},
            "policy_version": policy,
            "gold_matches_current": gold_matches,
            "tool_call": {"case_id": cid, "tool": tool_name, "args": dict(args_v1)},
        })
    # Force the named Harbor regression plant
    plant = next(c for c in cases if c["case_id"] == "t-320118")
    plant["slice"] = "fee"
    plant["baseline"] = {"text_pass": True, "tool_pass": True}
    plant["candidate"] = {"text_pass": True, "tool_pass": False}
    plant["tool_call"] = {"case_id": "t-320118", "tool": "explain_fee", "args": {"loan_id": "L-1118", "fee_code": "LATE"}}
    plant["policy_version"] = "p3"
    plant["gold_matches_current"] = True

    digest = hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()[:12]
    payload = {
        "kind": "SIMULATED",
        "seed": SEED,
        "n": N,
        "digest": digest,
        "schema_v1": SCHEMA_V1,
        "schema_v2_silent": SCHEMA_V2_SILENT,
        "baseline_pin": "compass-hardship-2028-07-a",
        "candidate_pin": "compass-hardship-2028-08-b",
        "current_policy_version": "p3",
        "cases": cases,
    }
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"n": N, "digest": digest, "plant": "t-320118"}, indent=2))

if __name__ == "__main__":
    main()
