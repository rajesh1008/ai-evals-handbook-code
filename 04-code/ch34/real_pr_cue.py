"""Modest REAL Anthropic: classify PR-gate cues. Usage: --live. Never print key."""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
OUT=Path(__file__).parent/'out'; CACHE=OUT/'real_pr_cue.json'
MODEL='claude-haiku-4-5-20251001'
CASES=[
('block','Fast suite green; slow suite 12/80 judge fails on fee slice.'),
('promote','Deterministic+fast+slow green; flake rate 0.0; canary ready.'),
('block','Schema check failed on candidate prompt render.'),
('block_flake','Slow would pass; judge flip rate 0.40 on fee canary.'),
('promote','Only similarity 0.81 above floor 0.70; judges green.'),
('block','Fast suite pass_rate 0.90; one pattern check failed.'),
('block','Prompt change passes fast, fails slow on hardship.'),
('promote','Cost $0.16 fast; slow deferred to nightly; PR smoke green.'),
('block_flake','Correct release; flaky judge quarantined? No — still in PR gate.'),
('promote','Flaky judge quarantined to nightly; PR gate green.'),
('block','Median days still 11; gates not wired to Actions.'),
('promote','Median PR-to-prod 2 days after Signature 9 ladder.'),
('block','Judge called before schema; order wrong.'),
('promote','Deterministic first; judge only in slow suite.'),
('block','Vendor claim without Harbor digest in workflow record.'),
('promote','workflow_record includes digest and pr_id.'),
('block','Nightly flake ignored; promoted on single green run.'),
('promote','Two-run confirm after near-threshold delta.'),
('block','Infrastructure timeout counted as product fail.'),
('promote','Timeouts separated as could_not_run.'),
('block','Aesthetic prompt punctuation skipped digest bump.'),
('promote','Digest updated; fast+slow green.'),
('block','Slow suite skipped to save cost on ship-critical PR.'),
('promote','Ship-critical PR paid slow suite cost $1.36.'),
]
PROMPT='Harbor PR-gate review. JSON only: {"verdict":"block"|"block_flake"|"promote","reason":"short"}\nCase:\n'

def call(text):
    import anthropic
    client=anthropic.Anthropic()
    msg=client.messages.create(model=MODEL,max_tokens=80,messages=[{'role':'user','content':PROMPT+text}])
    raw=msg.content[0].text.strip(); a,b=raw.find('{'), raw.rfind('}')
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
