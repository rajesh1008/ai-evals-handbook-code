from truss.prgate import (
    deterministic_checks, run_suite, flake_rate, gate_ladder_decision, ci_cost,
    pair_failures_to_main, quarantine_decision, debug_slow_regression,
)

def test_deterministic_schema():
    d=deterministic_checks({'schema_ok':False,'pattern_ok':True,'status':'ok','similarity':0.9})
    assert d['pass'] is False and 'schema' in d['fails']

def test_fast_vs_slow():
    cases=[{'id':'a','schema_ok':True,'pattern_ok':True,'status':'ok','similarity':0.9,'judge_ok':False}]
    assert run_suite(cases, mode='fast')['n_pass']==1
    assert run_suite(cases, mode='slow')['n_pass']==0

def test_flake_quarantine():
    fr=flake_rate([True,False,True,False,True])
    assert fr['quarantine'] is True

def test_ladder_promote_and_block():
    assert gate_ladder_decision(deterministic_pass=True,fast_pass=True,slow_pass=True,flake_blocked=False)['decision']=='PROMOTE'
    assert gate_ladder_decision(deterministic_pass=True,fast_pass=True,slow_pass=False,flake_blocked=False)['decision']=='BLOCK'

def test_ci_cost():
    c=ci_cost(10, cost_per_case=0.1, repeats=2, judge_share=0.5)
    assert c['total_usd']==2.0


def test_provenance_pairing_and_debug():
    # SIMULATED: 19 slow judge fails; 5 also red on main → 14 new regressions
    pr, main = [], []
    for i in range(80):
        pr.append({"id": f"c{i:02d}", "ok": i >= 19, "det": {"pass": True}, "flake": i == 0})
        main.append({"id": f"c{i:02d}", "ok": i >= 5})
    paired = pair_failures_to_main(pr, main)
    assert paired["fixture_status"] == "SIMULATED"
    assert paired["new_regression_count"] == 14
    assert paired["broken_window_count"] == 5
    suite = {"mode": "slow", "n": 80, "n_pass": 61, "pass_rate": 0.7625, "rows": [
        {"id": f"c{i:02d}", "det": {"pass": True}, "ok": i >= 19, "flake": i == 0} for i in range(80)
    ]}
    dbg = debug_slow_regression(suite, paired=paired)
    assert dbg["n_judge_fail"] == 19 and dbg["provenance"]["new_regression_count"] == 14

def test_quarantine_decision_actions():
    q = quarantine_decision("judge-fee-flaky", [True, False, True, False, True], flake_floor=0.1, min_flips=2)
    assert q["action"] == "QUARANTINE" and q["fixture_status"] == "SIMULATED"
    s = quarantine_decision("always-wrong", [False] * 5, flake_floor=0.1, min_flips=2)
    assert s["action"] == "HARD_FAIL_STABLE"
    b = quarantine_decision("one-flip", [True, True, True, True, False], flake_floor=0.1, min_flips=2)
    assert b["action"] == "HARD_FAIL" and b["quarantine"] is False
