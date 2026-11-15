from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'truss'))
from truss.prgate import run_suite, flake_rate, quarantine, ci_cost, gate_ladder_decision, workflow_record

OUT=Path(__file__).parent/'out'

def main():
    fix=json.loads((OUT/'fixture.json').read_text())
    base_fast=run_suite(fix['baseline_cases'], mode='fast')
    base_slow=run_suite(fix['baseline_cases'], mode='slow')
    cand_fast=run_suite(fix['candidate_cases'], mode='fast')
    cand_slow=run_suite(fix['candidate_cases'], mode='slow')
    # Lab teaching: candidate passes fast, fails slow
    teaching={
        'candidate_passes_fast': cand_fast['pass_rate']==1.0 or cand_fast['n_pass']==cand_fast['n'],
        'candidate_fails_slow': cand_slow['n_pass'] < cand_slow['n'],
        'slow_fail_count': cand_slow['n']-cand_slow['n_pass'],
    }
    # Actually fast may be 1.0 if all det pass
    teaching['candidate_passes_fast']=cand_fast['n_pass']==cand_fast['n']
    fr=flake_rate(fix['flake_repeats'])
    q=quarantine([{'id':'judge-fee-flaky','flake_rate':fr['fail_rate']}], flake_floor=0.10)
    cost_fast=ci_cost(80, cost_per_case=0.002, repeats=1, judge_share=0.0)
    cost_slow=ci_cost(80, cost_per_case=0.02, repeats=1, judge_share=0.85)
    ladder=gate_ladder_decision(
        deterministic_pass=True,
        fast_pass=teaching['candidate_passes_fast'],
        slow_pass=not teaching['candidate_fails_slow'],
        flake_blocked=False,
    )
    wf=workflow_record(fix['pr_id'], ladder['decision'], fix['digest'])
    out={
        'seed': fix['seed'],
        'digest': fix['digest'],
        'simulated': True,
        'baseline_fast': {k:base_fast[k] for k in ('mode','n','n_pass','pass_rate')},
        'baseline_slow': {k:base_slow[k] for k in ('mode','n','n_pass','pass_rate')},
        'candidate_fast': {k:cand_fast[k] for k in ('mode','n','n_pass','pass_rate')},
        'candidate_slow': {k:cand_slow[k] for k in ('mode','n','n_pass','pass_rate')},
        'teaching': teaching,
        'flake': fr,
        'quarantine': q,
        'cost_fast_usd': cost_fast,
        'cost_slow_usd': cost_slow,
        'ladder': ladder,
        'workflow': wf,
        'median_days_before': fix['median_days_before'],
        'median_days_after': fix['median_days_after'],
        'study_window': fix['study_window'],
        'scoreboard_date': fix['scoreboard_date'],
    }
    (OUT/'lab.json').write_text(json.dumps(out, indent=2))
    print(json.dumps({k:out[k] for k in out if k not in ()}, indent=2)[:2000])
if __name__=='__main__':
    main()
