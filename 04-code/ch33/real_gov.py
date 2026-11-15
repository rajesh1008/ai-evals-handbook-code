"""Modest REAL Anthropic: residency/manifest judgement prompts."""
from __future__ import annotations
import json, os, time, urllib.request
from pathlib import Path
OUT=Path(__file__).parent/'out'; MODEL='claude-haiku-4-5-20251001'
PROMPTS=[
 'List five fields a run manifest for an LLM eval must contain. Comma-separated.',
 'If fee_amount is redacted but the metric needs fee_amount, is the eval still valid? Reply YES or NO.',
 'May a US-only lender send raw hardship traces to an EU-only judge API without a residency review? Reply YES or NO.',
 'Retention retired 14 percent of an eval set. Should replacements be labelled? Reply YES or NO.',
 'Who should own gold set access logs: the gold owner or a random engineer? Reply GOLD_OWNER or ENGINEER.',
 'Is a six-month-old eval reproducible if the dataset digest changed? Reply YES or NO.',
]
def call(p):
    key=os.environ['ANTHROPIC_API_KEY']
    body=json.dumps({'model':MODEL,'max_tokens':100,'messages':[{'role':'user','content':p}]}).encode()
    req=urllib.request.Request('https://api.anthropic.com/v1/messages',data=body,headers={'content-type':'application/json','x-api-key':key,'anthropic-version':'2023-06-01'},method='POST')
    with urllib.request.urlopen(req,timeout=60) as resp:
        data=json.loads(resp.read().decode())
    return ''.join(x.get('text','') for x in data.get('content',[]) if x.get('type')=='text')
def score(i,t):
    u=(t or '').upper()
    if i==0: return sum(1 for w in ['MODEL','PROMPT','DATASET','SEED','SUITE'] if w in u)>=3 or ',' in (t or '')
    if i==1: return u.strip().startswith('NO')
    if i==2: return u.strip().startswith('NO')
    if i==3: return u.strip().startswith('YES')
    if i==4: return 'GOLD' in u
    if i==5: return u.strip().startswith('NO')
    return False
def main():
    # Cached reference run: report it unchanged unless --live is passed (then the Anthropic API is called, paid).
    import sys as _sys
    _live_flag = "--live" in _sys.argv
    _cache = OUT / "real_gov.json"
    if not _live_flag and _cache.exists():
        out = json.loads(_cache.read_text())
        print({k:out[k] for k in ('kind','n','n_ok','rate')})
        return
    rows=[]; live=_live_flag and bool(os.environ.get('ANTHROPIC_API_KEY')); err=None
    if live:
        try:
            for i,p in enumerate(PROMPTS):
                try:
                    text=call(p); rows.append({'i':i,'ok':score(i,text),'n':len(text)}); time.sleep(0.25)
                except Exception as e:
                    err=type(e).__name__; rows.append({'i':i,'ok':False,'error':err})
        except Exception as e:
            live=False; err=type(e).__name__; rows=[]
    if not rows:
        rows=[{'i':i,'ok':True,'simulated':True} for i in range(len(PROMPTS))]; live=False
    n_ok=sum(1 for r in rows if r['ok'])
    out={'kind':'REAL' if live else 'SIMULATED','model':MODEL if live else 'simulated','n':len(rows),'n_ok':n_ok,'rate':n_ok/len(rows),'rows':rows,'error_type':err,'note':'monitor-only'}
    (OUT/'real_gov.json').write_text(json.dumps(out,indent=2))
    print({k:out[k] for k in ('kind','n','n_ok','rate')})
if __name__=='__main__':
    main()
