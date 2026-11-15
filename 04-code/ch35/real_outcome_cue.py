"""Modest REAL Anthropic: offline/online surrogate cues. --live. Never print key."""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
OUT=Path(__file__).parent/'out'; CACHE=OUT/'real_outcome_cue.json'
MODEL='claude-haiku-4-5-20251001'
CASES=[
('trust_fee','Fee offline r=-0.62 with re-contact; tone r=0.05. Which proxy gates?'),
('reject_tone','Tone offline high; re-contact unchanged. Ship on tone?'),
('reject_delight','Delight score rises with complaints (r=+0.71). Gate on delight?'),
('need_cf','Want offline ship without A/B; no counterfactual logs. Safe?'),
('list_signals','Name online signals Harbor tracks for Compass.'),
('honest_corr','Offline fee improves 4pts; re-contact flat across releases. Surrogate?'),
('trust_fee','Fee explanation score predicts lower re-contact across 40 weeks.'),
('reject_tone','Tone score predicts nothing useful online.'),
('reject_delight','Proxy anti-correlates with harm signal.'),
('need_cf','Counterfactual logging incomplete; policy_hash missing.'),
('trust_fee','Signature 8 marks fee usable, tone failed.'),
('reject_tone','Ship because users liked the tone in offline panel.'),
('honest_corr','Report r with n and signal name, not vibes.'),
('list_signals','resolution, re_contact, escalation, complaint.'),
('reject_delight','Satisfaction up, complaints up — refuse gate.'),
('need_cf','Design CF log: shown_arm, alt arms, policy_hash.'),
('trust_fee','Use fee offline to prioritise, still audit online.'),
('reject_tone','Tone is not a surrogate for borrower outcomes.'),
('honest_corr','Trial-level surrogacy not unit agreement with judges.'),
('list_signals','Online signals are business events, not judge Likert.'),
('reject_delight','BAD_PROXY label from anti_correlation_injection.'),
('trust_fee','Harbor scoreboard: fee predicts; tone predicts nothing.'),
('need_cf','Without CF logs, offline ranking is not a ship ticket.'),
('honest_corr','Weak pooled surrogacy means send to live experiment.'),
]
PROMPT='Harbor offline→online review. JSON only: {"verdict":"trust_fee"|"reject_tone"|"reject_delight"|"need_cf"|"list_signals"|"honest_corr","reason":"short"}\nCase:\n'

def call(text):
    import anthropic
    client=anthropic.Anthropic()
    msg=client.messages.create(model=MODEL,max_tokens=80,messages=[{'role':'user','content':PROMPT+text}])
    raw=msg.content[0].text.strip(); a,b=raw.find('{'),raw.rfind('}')
    return json.loads(raw[a:b+1]) if a>=0 and b>a else {'raw':raw}

def main():
    live='--live' in sys.argv
    if CACHE.exists() and not live:
        print(json.dumps({k:v for k,v in json.loads(CACHE.read_text()).items() if k!='rows'}, indent=2)); return
    if not os.environ.get('ANTHROPIC_API_KEY'):
        CACHE.write_text(json.dumps({'status':'pending','n':0})); return
    rows=[]; correct=0
    for gold,desc in CASES:
        j=call(desc); pred=j.get('verdict'); ok=pred==gold; correct+=int(ok)
        rows.append({'gold':gold,'pred':pred,'ok':ok,'desc':desc[:70]}); time.sleep(0.12)
    out={'status':'ok','model':MODEL,'n':len(rows),'correct':correct,'accuracy':correct/len(rows),'rows':rows,'simulated_suite':True}
    CACHE.write_text(json.dumps(out, indent=2))
    print(json.dumps({k:out[k] for k in out if k!='rows'}, indent=2))
if __name__=='__main__':
    main()
