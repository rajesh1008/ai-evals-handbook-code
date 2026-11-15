"""SIMULATED hardship trajectories for Chapter 24. Seed 2026. No model calls."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

SEED = 2026
N = 500
START_ID = 270001
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

TOOLS = ["get_loan", "get_borrower", "lookup_policy", "check_eligibility",
         "compute_plan", "draft_offer", "refer_officer", "ask_clarification"]

# Canonical happy path (reference length 5)
REF = [
    {"tool": "get_loan", "args": {"loan_id": "LOAN"}, "status": "ok"},
    {"tool": "get_borrower", "args": {"borrower_id": "BOR"}, "status": "ok"},
    {"tool": "lookup_policy", "args": {"topic": "hardship"}, "status": "ok"},
    {"tool": "check_eligibility", "args": {"loan_id": "LOAN", "reason": "REASON"}, "status": "ok"},
    {"tool": "draft_offer", "args": {"loan_id": "LOAN", "plan": "PLAN"}, "status": "ok"},
]

CHECKLIST = [
    {"id": "loan", "tool": "get_loan", "required_args": ["loan_id"]},
    {"id": "borrower", "tool": "get_borrower", "required_args": ["borrower_id"]},
    {"id": "policy", "tool": "lookup_policy", "required_args": ["topic"]},
    {"id": "elig", "tool": "check_eligibility", "required_args": ["loan_id", "reason"]},
    {"id": "offer_or_refer", "tool": None, "required_args": []},  # special: draft_offer OR refer_officer
]

REASONS = ["job_loss", "medical", "disaster", "income_drop", "bereavement"]
PLANS = ["defer_1", "defer_3", "reduce_payment", "extend_term"]

CONSTRAINT = "no offer when employment change is stated but unverified"


def _id(i: int) -> str:
    return f"t-{START_ID + i}"


def _loan(i: int) -> str:
    return f"HL-{100000 + i}"


def _bor(i: int) -> str:
    return f"B-{200000 + i}"


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]


def make_trajectory(rng: random.Random, i: int, kind: str) -> dict:
    """Build one hardship trajectory of a given failure/success kind."""
    loan, bor = _loan(i), _bor(i)
    reason = REASONS[i % len(REASONS)]
    plan = PLANS[i % len(PLANS)]
    tid = _id(i)
    stated_work = rng.random() < 0.08  # FM-26-ish share

    def step(tool, args, status="ok", **extra):
        s = {"tool": tool, "args": args, "status": status}
        s.update(extra)
        return s

    steps = []
    outcome_ok = True
    process_ok = True
    offer_plan = plan
    action = "draft"

    if kind == "clean":
        steps = [
            step("get_loan", {"loan_id": loan}),
            step("get_borrower", {"borrower_id": bor}),
            step("lookup_policy", {"topic": "hardship"}),
            step("check_eligibility", {"loan_id": loan, "reason": reason}),
            step("draft_offer", {"loan_id": loan, "plan": plan}),
        ]
    elif kind == "loop":
        # eligibility errors then retries get_loan (loop) then succeeds
        steps = [
            step("get_loan", {"loan_id": loan}),
            step("get_borrower", {"borrower_id": bor}),
            step("lookup_policy", {"topic": "hardship"}),
            step("check_eligibility", {"loan_id": loan, "reason": reason}, status="error"),
            step("get_loan", {"loan_id": loan}),  # loop
            step("check_eligibility", {"loan_id": loan, "reason": reason}),
            step("draft_offer", {"loan_id": loan, "plan": plan}),
        ]
    elif kind == "recover":
        steps = [
            step("get_loan", {"loan_id": loan}),
            step("get_borrower", {"borrower_id": bor}),
            step("lookup_policy", {"topic": "hardship"}, status="error"),
            step("lookup_policy", {"topic": "hardship"}),  # recovery
            step("check_eligibility", {"loan_id": loan, "reason": reason}),
            step("draft_offer", {"loan_id": loan, "plan": plan}),
        ]
    elif kind == "lucky":
        # Right offer via wrong tool with guessed argument (INJECTION)
        process_ok = False
        steps = [
            step("get_loan", {"loan_id": loan}),
            step("get_borrower", {"borrower_id": bor}),
            # Skips lookup_policy and check_eligibility; guesses via compute_plan
            step("compute_plan", {"loan_id": loan, "guess_reason": reason, "guess_plan": plan}),
            step("draft_offer", {"loan_id": loan, "plan": plan}),
        ]
        action = "draft"
    elif kind == "wrong_offer":
        outcome_ok = False
        process_ok = False
        bad_plan = PLANS[(i + 1) % len(PLANS)]
        offer_plan = bad_plan
        steps = [
            step("get_loan", {"loan_id": loan}),
            step("get_borrower", {"borrower_id": bor}),
            step("lookup_policy", {"topic": "hardship"}),
            step("check_eligibility", {"loan_id": loan, "reason": reason}),
            step("draft_offer", {"loan_id": loan, "plan": bad_plan}),
        ]
    elif kind == "refer":
        steps = [
            step("get_loan", {"loan_id": loan}),
            step("get_borrower", {"borrower_id": bor}),
            step("lookup_policy", {"topic": "hardship"}),
            step("check_eligibility", {"loan_id": loan, "reason": reason}),
            step("refer_officer", {"loan_id": loan, "why": "stated_work" if stated_work else "edge"}),
        ]
        action = "refer"
        offer_plan = None
    elif kind == "abandon":
        outcome_ok = False
        process_ok = False
        steps = [
            step("get_loan", {"loan_id": loan}),
            step("ask_clarification", {"question": "which_loan"}),
            step("ask_clarification", {"question": "which_loan"}),  # loop
            step("ask_clarification", {"question": "income"}),
        ]
        action = "abandon"
        offer_plan = None
    elif kind == "missing_elig":
        # Completes without eligibility check (false completion risk)
        process_ok = False
        outcome_ok = True  # happens to draft a correct-looking plan
        steps = [
            step("get_loan", {"loan_id": loan}),
            step("get_borrower", {"borrower_id": bor}),
            step("lookup_policy", {"topic": "hardship"}),
            step("draft_offer", {"loan_id": loan, "plan": plan}),
        ]
    else:
        raise ValueError(kind)

    # Compaction texts
    full_constraint_ctx = (
        f"Policy constraint: {CONSTRAINT}. "
        f"Borrower {bor} loan {loan} reason {reason}. "
        + ("Borrower stated employment change; unverified. " if stated_work else "")
        + "Prior tool results retained in full."
    )
    # Most compactors drop the constraint ~30% of the time when long
    drop = rng.random() < 0.30
    if drop:
        compacted = (
            f"Summary: hardship request for {loan}, reason {reason}. "
            + ("Employment mentioned. " if stated_work else "")
            + "Continue to offer step."
        )
    else:
        compacted = (
            f"Summary: hardship for {loan}. Constraint: {CONSTRAINT}. "
            f"Reason {reason}."
            + (" Stated work change unverified." if stated_work else "")
        )

    # Checklist satisfaction for offer_or_refer
    has_terminal = any(s["tool"] in ("draft_offer", "refer_officer") for s in steps)

    return {
        "trace_id": tid,
        "kind": kind,
        "loan_id": loan,
        "borrower_id": bor,
        "reason": reason,
        "plan": plan,
        "offer_plan": offer_plan,
        "action": action,
        "stated_work": stated_work,
        "steps": steps,
        "outcome_ok": outcome_ok,
        "process_ok": process_ok,
        "reference": [
            {**REF[0], "args": {"loan_id": loan}},
            {**REF[1], "args": {"borrower_id": bor}},
            {**REF[2], "args": {"topic": "hardship"}},
            {**REF[3], "args": {"loan_id": loan, "reason": reason}},
            {**REF[4], "args": {"loan_id": loan, "plan": plan}},
        ] if action == "draft" and kind not in ("refer", "abandon") else None,
        "full_context": full_constraint_ctx,
        "compacted": compacted,
        "compaction_dropped": drop,
        "has_terminal": has_terminal,
    }


def build(n: int = N, seed: int = SEED) -> list:
    rng = random.Random(seed)
    # Target mix approximating Blueprint: ~23% loop; lucky passes planted; clean majority
    # 500 traj: clean 250, loop 115 (~23%), recover 40, lucky 30, wrong_offer 25,
    # refer 20, abandon 10, missing_elig 10
    mix = (["clean"] * 250 + ["loop"] * 115 + ["recover"] * 40 + ["lucky"] * 30
           + ["wrong_offer"] * 25 + ["refer"] * 20 + ["abandon"] * 10 + ["missing_elig"] * 10)
    assert len(mix) == n
    rng.shuffle(mix)
    trajs = [make_trajectory(rng, i, mix[i]) for i in range(n)]
    # Pin a named lucky pass for the chapter narrative
    for i, t in enumerate(trajs):
        if t["kind"] == "lucky":
            # Force ID t-270087 if possible by swapping with index 86
            target = 86  # 270001+86 = 270087
            if i != target:
                other = trajs[target]
                # rebuild both with swapped kinds but keep indices for IDs
                trajs[target] = make_trajectory(rng, target, "lucky")
                trajs[i] = make_trajectory(rng, i, other["kind"])
            break
    return trajs


def build_passk(n_tasks: int = 50, k: int = 5, seed: int = SEED) -> list:
    """50 tasks × 5 trials. Per-task success probability varies."""
    rng = random.Random(seed + 7)
    tasks = []
    for t in range(n_tasks):
        # p_success around 0.55 to 0.95
        p = 0.55 + 0.40 * rng.random()
        trials = [rng.random() < p for _ in range(k)]
        tasks.append({
            "task_id": f"t-{271001 + t}",
            "p": round(p, 3),
            "trials": trials,
            "n_success": sum(trials),
        })
    return tasks


def main():
    trajs = build()
    tasks = build_passk()
    payload = {
        "seed": SEED,
        "n": len(trajs),
        "digest": _digest([t["trace_id"] for t in trajs]),
        "kind_counts": {k: sum(1 for t in trajs if t["kind"] == k)
                        for k in sorted({t["kind"] for t in trajs})},
        "looped": sum(1 for t in trajs if t["kind"] == "loop"),
        "trajectories": trajs,
        "passk_tasks": tasks,
        "constraint": CONSTRAINT,
        "named_lucky": "t-270087",
    }
    path = OUT / "fixture.json"
    path.write_text(json.dumps(payload))
    print(f"wrote {path} n={len(trajs)} digest={payload['digest']}")
    print("kinds:", payload["kind_counts"])
    print("loop share:", payload["looped"] / len(trajs))
    lucky = next(t for t in trajs if t["trace_id"] == "t-270087")
    print("named lucky kind:", lucky["kind"], "tools:", [s["tool"] for s in lucky["steps"]])


if __name__ == "__main__":
    main()
