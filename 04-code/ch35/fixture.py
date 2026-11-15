"""SIMULATED Harbor offline→online fixture (seed 2035)."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path
OUT=Path(__file__).parent/'out'; SEED=2035; N=40

def main():
    rng=random.Random(SEED)
    # Weekly releases: offline fee/tone scores + online rates
    fee, tone, recontact, complaint, resolution, escalation = [], [], [], [], [], []
    for i in range(N):
        # fee quality high → recontact low (negative corr)
        f = rng.uniform(0.55, 0.95)
        noise = rng.gauss(0, 0.04)
        rc = max(0.02, min(0.35, 0.40 - 0.38*f + noise))
        # tone independent of recontact / weakly related
        t = rng.uniform(0.60, 0.95)
        # injection series: tone-like satisfaction rises with complaints (anti-pattern)
        # separate parallel series for injection
        fee.append(round(f, 4)); tone.append(round(t, 4))
        recontact.append(round(rc, 4))
        complaint.append(round(max(0.01, min(0.25, 0.20 - 0.15*f + rng.gauss(0,0.03))), 4))
        resolution.append(round(max(0.5, min(0.95, 0.4 + 0.5*f + rng.gauss(0,0.05))), 4))
        escalation.append(round(max(0.01, min(0.2, 0.18 - 0.12*f + rng.gauss(0,0.02))), 4))
    # Bad proxy injection: "delight" score tracks compliments while complaints rise
    delight, complaints_inj = [], []
    for i in range(N):
        c = rng.uniform(0.05, 0.30)
        d = max(0.4, min(0.99, 0.5 + 1.2*c + rng.gauss(0, 0.03)))  # positive with complaints
        delight.append(round(d, 4)); complaints_inj.append(round(c, 4))
    rows=[{
        'week': i+1,
        'fee_offline': fee[i],
        'tone_offline': tone[i],
        're_contact': recontact[i],
        'complaint': complaint[i],
        'resolution': resolution[i],
        'escalation': escalation[i],
        'id': f't-{350100+i}',
    } for i in range(N)]
    blob={
        'seed': SEED, 'simulated': True, 'label': 'SIMULATED', 'n_weeks': N,
        'rows': rows,
        'injection': {'delight': delight, 'complaints': complaints_inj},
        'study_window': 'Mon 15 Jan 2029 – Mon 12 Mar 2029',
        'scoreboard_date': 'Mon 12 Mar 2029',
        'harbor': {
            'fee_predicts_recontact': True,
            'tone_predicts_nothing': True,
        },
    }
    raw=json.dumps({'fee':fee,'tone':tone,'rc':recontact,'delight':delight,'seed':SEED}, sort_keys=True)
    blob['digest']=hashlib.sha256(raw.encode()).hexdigest()[:12]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'fixture.json').write_text(json.dumps(blob, indent=2))
    print(json.dumps({'digest':blob['digest'],'n':N}, indent=2))
if __name__=='__main__':
    main()
