from __future__ import annotations
import json,os,urllib.request
from pathlib import Path
OUT=Path(__file__).parent/'out'
MODEL='claude-haiku-4-5-20251001'
PROMPTS=[
    'In one sentence, what is shadow mode for an LLM agent release?',
    'Why must tools run dry-run in shadow? One sentence.',
    'Why is overall agreement misleading for hardship? One sentence.',
    'Write a numeric exit rule example for shadow promote. One sentence.',
    'Name one thing shadow mode cannot detect. One sentence.',
    'Should a shadow tool with side effects abort the run? Yes or no and why, one sentence.',
]
def call(prompt):
    key=os.environ.get('ANTHROPIC_API_KEY')
    if not key: raise RuntimeError('missing key')
    body=json.dumps({"model":MODEL,"max_tokens":120,"messages":[{"role":"user","content":prompt}]}).encode()
    req=urllib.request.Request('https://api.anthropic.com/v1/messages',data=body,headers={'content-type':'application/json','x-api-key':key,'anthropic-version':'2023-06-01'},method='POST')
    with urllib.request.urlopen(req,timeout=60) as resp:
        data=json.loads(resp.read().decode())
    return '\n'.join(b.get('text','') for b in data.get('content',[]) if b.get('type')=='text').strip()
def main():
    # Cached reference run: report it unchanged unless --live is passed (then the Anthropic API is called, paid).
    import sys as _sys
    _live_flag = "--live" in _sys.argv
    _cache = OUT / "real_shadow.json"
    if not _live_flag and _cache.exists():
        out = json.loads(_cache.read_text())
        print({k:out[k] for k in ('kind','n','n_ok','rate','error_type','note')})
        return
    if not _live_flag:
        print("no cached run at out/real_shadow.json and --live not given; not calling the API (see OUTPUT.txt)")
        return
    rows=[]; n_ok=0; err=None
    try:
        for i,p in enumerate(PROMPTS):
            a=call(p); ok=len(a.split())>=6
            n_ok+=int(ok); rows.append({"i":i,"ok":ok,"n":len(a.split())})
    except Exception as e:
        err=type(e).__name__
    out={"kind":"REAL","model":MODEL,"n":len(PROMPTS),"n_ok":n_ok,"rate":n_ok/len(PROMPTS),"rows":rows,"error_type":err,"note":"monitor-only"}
    (OUT/'real_shadow.json').write_text(json.dumps(out,indent=2))
    print({k:out[k] for k in ('kind','n','n_ok','rate','error_type','note')})
if __name__=='__main__':
    main()
