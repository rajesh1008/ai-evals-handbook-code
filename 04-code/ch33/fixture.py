"""SIMULATED governance fixture Chapter 33 (seed 2033)."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path
OUT=Path(__file__).parent/'out'; OUT.mkdir(exist_ok=True)
SEED=2033; N=500

def main():
    rng=random.Random(SEED)
    cases=[]
    for i in range(N):
        age=rng.randint(1,400)
        fee=round(rng.uniform(15,85),2)
        cases.append({
            'case_id': f'e-{340101+i}',
            'age_days': age,
            'fee_amount': fee,
            'fee_amount_redacted': '[REDACTED]',
            'loan_token': f'TOK-{1000+i}',
            'region': rng.choice(['us-west','us-east','eu-central']),
        })
    # force ~14% retire at retain_days=180 with age>180
    # adjust ages to hit ~14%
    n_retire=int(round(0.14*N))
    for i,c in enumerate(cases):
        c['age_days']=200+i%50 if i<n_retire else rng.randint(1,170)
    old_manifest={
        'run_id':'run-2028-03-15-hardship',
        'model_pin':'compass-hardship-2028-03-a',
        'prompt_digest':'a1b2c3d4e5f6',
        'dataset_digest':'oldset9f3a2b',
        'seed':2028,
        'suite':'hardship-fee-v3',
        'created_at':'2028-03-15',
        'residency':'us-west',
        'owner':'Ryan Mitchell',
    }
    digest=hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest()[:12]
    payload={'kind':'SIMULATED','seed':SEED,'digest':digest,'n':N,'cases':cases,'old_manifest':old_manifest,
             'available_now':{**old_manifest,'dataset_digest':digest}, # dataset refreshed
             'retain_days':180,'metric_fields':['fee_amount'],'allowed_regions':['us-west','us-east']}
    (OUT/'fixture.json').write_text(json.dumps(payload))
    print(json.dumps({'n':N,'digest':digest,'n_retire_target':n_retire},indent=2))
if __name__=='__main__':
    main()
