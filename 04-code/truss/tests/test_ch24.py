"""Tests for truss.trajectory (Chapter 24). Seven tests, matching prior chapters."""
from truss.trajectory import (
    score_step, score_trajectory, detect_loops, recovery, lucky_pass,
    transition_matrix, pass_hat_k, pass_at_k, pass_hat_k_unbiased,
    aggregate_pass_hat_k, compaction_survives, step_efficiency,
)


def test_score_step_tool_and_args():
    step = {"tool": "lookup_policy", "args": {"loan_id": "L1", "reason": "job_loss"}, "status": "ok"}
    exp = {"tool": "lookup_policy", "args": {"loan_id": "L1", "reason": "job_loss"}}
    sc = score_step(step, exp, required_args=["loan_id", "reason"])
    assert sc["pass"] and sc["tool_ok"] and sc["args_match"]
    bad = score_step({"tool": "guess_offer", "args": {"loan_id": "L1"}, "status": "ok"}, exp,
                     required_args=["loan_id", "reason"])
    assert not bad["tool_ok"] and not bad["pass"] and not bad["args_present"]


def test_score_trajectory_reference_and_checklist():
    steps = [
        {"tool": "get_loan", "args": {"id": "L1"}, "status": "ok"},
        {"tool": "check_eligibility", "args": {"id": "L1", "months": 12}, "status": "ok"},
        {"tool": "draft_offer", "args": {"id": "L1", "plan": "defer_3"}, "status": "ok"},
    ]
    ref = list(steps)
    r = score_trajectory(steps, reference=ref)
    assert r["exact_match"] and r["partial"] == 1.0 and r["mode"] == "reference"
    short = score_trajectory(steps[:2], reference=ref)
    assert short["length_mismatch"] and not short["exact_match"]
    checklist = [
        {"id": "loan", "tool": "get_loan", "args": {"id": "L1"}},
        {"id": "elig", "tool": "check_eligibility", "args": {"id": "L1", "months": 12}},
        {"id": "offer", "tool": "draft_offer", "args": {"id": "L1", "plan": "defer_3"}},
    ]
    c = score_trajectory(steps, checklist=checklist)
    assert c["exact_match"] and c["partial"] == 1.0 and c["credited"] == ["loan", "elig", "offer"]
    # wrong tool mid-way still credits other checklist items in any order
    wrong = [
        {"tool": "get_loan", "args": {"id": "L1"}, "status": "ok"},
        {"tool": "guess_offer", "args": {"id": "L1", "plan": "defer_3"}, "status": "ok"},
        {"tool": "draft_offer", "args": {"id": "L1", "plan": "defer_3"}, "status": "ok"},
    ]
    c2 = score_trajectory(wrong, checklist=checklist)
    assert c2["step_passes"] == 2 and abs(c2["partial"] - 2 / 3) < 1e-12


def test_detect_loops_and_efficiency():
    steps = [
        {"tool": "get_loan", "args": {"id": "L1"}, "status": "ok"},
        {"tool": "check_eligibility", "args": {"id": "L1"}, "status": "error"},
        {"tool": "get_loan", "args": {"id": "L1"}, "status": "ok"},  # loop
        {"tool": "check_eligibility", "args": {"id": "L1"}, "status": "ok"},
    ]
    d = detect_loops(steps)
    assert d["looped"] and d["n_loops"] >= 1
    eff = step_efficiency(steps, reference_len=3)
    assert eff["n_steps"] == 4 and eff["extra_steps"] == 1 and abs(eff["efficiency"] - 0.75) < 1e-12


def test_recovery_and_lucky_pass():
    steps = [
        {"tool": "fee_lookup", "args": {}, "status": "error"},
        {"tool": "fee_lookup", "args": {}, "status": "ok"},
        {"tool": "other", "args": {}, "status": "error"},
    ]
    r = recovery(steps)
    assert r["n_errors"] == 2 and r["n_recovered"] == 1 and abs(r["rate"] - 0.5) < 1e-12
    assert lucky_pass(True, False)["is_lucky_pass"] and lucky_pass(True, False)["kind"] == "lucky_pass"
    assert lucky_pass(True, True)["kind"] == "true_success"
    assert lucky_pass(False, True)["kind"] == "false_failure"
    assert lucky_pass(False, False)["kind"] == "true_failure"


def test_transition_matrix_failure_rates():
    trajs = [
        [{"tool": "A", "status": "ok"}, {"tool": "B", "status": "error"}],
        [{"tool": "A", "status": "ok"}, {"tool": "B", "status": "ok"}],
        [{"tool": "A", "status": "ok"}, {"tool": "C", "status": "ok"}],
    ]
    m = transition_matrix(trajs)
    assert m["counts"][("A", "B")] == 2
    assert m["fails"][("A", "B")] == 1
    assert abs(m["rates"][("A", "B")] - 0.5) < 1e-12
    assert m["n_trajectories"] == 3


def test_pass_hat_k_and_unbiased():
    assert pass_hat_k([True, True, True, True, True]) == 1.0
    assert pass_hat_k([True, True, False, True, True]) == 0.0
    assert pass_at_k([False, False, True]) == 1.0
    assert pass_at_k([False, False, False]) == 0.0
    # C(5,5)/C(5,5)=1; C(4,5)=0
    assert abs(pass_hat_k_unbiased(5, 5, 5) - 1.0) < 1e-12
    assert pass_hat_k_unbiased(5, 4, 5) == 0.0
    # C(4,3)/C(5,3) = 4/10 = 0.4
    assert abs(pass_hat_k_unbiased(5, 4, 3) - 0.4) < 1e-12
    agg = aggregate_pass_hat_k([
        [True, True, True, True, True],
        [True, False, True, True, True],
        [False, False, False, False, False],
    ], k=5)
    assert agg["n_pass_hat_k"] == 1 and agg["n_pass_at_k"] == 2
    assert abs(agg["pass_hat_k"] - 1 / 3) < 1e-12


def test_compaction_survives_constraint():
    c = compaction_survives(
        "no offer when employment change is stated but unverified",
        "Borrower stated a job change. Policy: no offer when employment change is stated but unverified.",
    )
    assert c["survives"]
    c2 = compaction_survives(
        "no offer when employment change is stated but unverified",
        "Borrower asked about hardship. Prior turns summarised.",
        aliases=["stated-work check", "FM-26"],
    )
    assert not c2["survives"]
    c3 = compaction_survives("X", "notes about FM-26 apply", aliases=["FM-26"])
    assert c3["survives"] and "fm-26" in c3["found"]
