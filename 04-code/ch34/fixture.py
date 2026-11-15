"""SIMULATED Harbor PR-gate fixture (seed 2034)."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path
OUT=Path(__file__).parent/'out'; SEED=2034

def main():
    rng=random.Random(SEED)
    # Baseline cases: deterministic mostly green; slow judge mostly green
    cases=[]
    for i in range(80):
        cases.append({
            'id': f't-{340100+i}',
            'schema_ok': True,
            'pattern_ok': True,
            'status': 'ok',
            'similarity': round(rng.uniform(0.72, 0.98), 3),
            'similarity_floor': 0.70,
            'judge_ok': rng.random() < 0.92,
            'flake_rate': 0.0,
        })
    # Candidate prompt change: fast still green; slow judge regresses on fee slice
    cand=[dict(c) for c in cases]
    for c in cand[0:12]:
        c['judge_ok']=False  # slow-suite fails
    # Flaky judge case repeats for injection
    flake_repeats=[True, False, True, False, True]  # flake_rate 0.4
    blob={
        'seed': SEED,
        'simulated': True,
        'label': 'SIMULATED',
        'baseline_cases': cases,
        'candidate_cases': cand,
        'flake_repeats': flake_repeats,
        'median_days_before': 11,
        'median_days_after': 2,
        'study_window': 'Mon 4 Dec 2028 – Mon 8 Jan 2029',
        'scoreboard_date': 'Mon 8 Jan 2029',
        'pr_id': 'pr-4821',
    }
    raw=json.dumps({'seed':SEED,'cand_fail':12,'n':80,'flake':flake_repeats}, sort_keys=True)
    blob['digest']=hashlib.sha256(raw.encode()).hexdigest()[:12]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'fixture.json').write_text(json.dumps(blob, indent=2))
    print(json.dumps({'digest':blob['digest'],'n':80,'slow_fails':12}, indent=2))
if __name__=='__main__':
    main()
