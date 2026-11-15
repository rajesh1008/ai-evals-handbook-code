from __future__ import annotations
import hashlib, json, random
from pathlib import Path
OUT=Path(__file__).parent/'out'; OUT.mkdir(exist_ok=True)
SEED=2038
N=2000
N_HARD=250  # 220/250=0.88
N_AGREE_HARD=220
N_AGREE_OVERALL=1922  # 0.961

def main():
    rng=random.Random(SEED)
    rows=[]
    # hardship: first 250
    for i in range(N_HARD):
        agree = i < N_AGREE_HARD
        rows.append({"id": f"s-{340000+i}", "flow": "hardship", "risk_tier": "high", "agree": agree,
                     "prod_reply": "prod", "cand_reply": "prod" if agree else "cand_diff"})
    # remaining flows to hit overall agree count
    remain=N-N_HARD
    n_agree_rest=N_AGREE_OVERALL-N_AGREE_HARD
    flows=["fee","account","payoff","lien","statement"]
    for i in range(remain):
        agree = i < n_agree_rest
        rows.append({"id": f"s-{340000+N_HARD+i}", "flow": flows[i%len(flows)], "risk_tier": "std", "agree": agree,
                     "prod_reply": "prod", "cand_reply": "prod" if agree else "cand_diff"})
    rng.shuffle(rows)
    # restore deterministic order by id for digest stability
    rows=sorted(rows, key=lambda r: r["id"])
    dry=["get_balance","get_fee_schedule","lookup_hardship_policy","draft_offer_preview"]
    payload={"kind":"SIMULATED","seed":SEED,"n":N,"rows":rows,"dry_run_allowlist":dry,
             "exit_floors":{"overall":0.98,"hardship":0.95},
             "candidate_pin":"compass-hardship-2028-12-c",
             "run_id":"shadow-2028-12-09","study_window":"2028-12-09 to 2028-12-11"}
    payload["digest"]=hashlib.sha256(json.dumps([(r["id"],r["flow"],int(r["agree"])) for r in rows],separators=(',',':')).encode()).hexdigest()[:12]
    (OUT/'fixture.json').write_text(json.dumps(payload))
    print(payload['digest'], sum(r['agree'] for r in rows)/N, sum(r['agree'] for r in rows if r['flow']=='hardship')/N_HARD)

if __name__=='__main__':
    main()
