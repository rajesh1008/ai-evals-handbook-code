"""Modest REAL Anthropic: classify gateway/migration review cues.
Usage: python3 real_pin_cue.py [--live]
Never prints API key.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
OUT = Path(__file__).parent / "out"
CACHE = OUT / "real_pin_cue.json"
MODEL = "claude-haiku-4-5-20251001"
CASES = [
    ("hold", "Hardship +2pts, fee +1pt, latency +18% slower on paired suite."),
    ("ship", "Hardship +1pt, fee +1pt, latency -5% faster; canary flips 0/40."),
    ("hold", "Same version string; canary flip rate 0.12 on frozen set."),
    ("hold", "Gateway mid-run model id changed from June pin to September pin."),
    ("ship", "Deprecation notice 75 days; suite green; no regressions."),
    ("hold", "Notice 20 days; suite not ready; one fee regression."),
    ("hold", "Judge model rotated; flip rate 0.08 on fee canary."),
    ("ship", "Pinned digest match; migration deltas all non-negative on lower-is-better latency."),
    ("hold", "Vendor claims +10% quality; Harbor paired suite shows fee -3pts."),
    ("hold", "Hidden date string in system prompt changed; outputs shift on canary."),
    ("ship", "Re-validation complete after model pin; triggers cleared."),
    ("hold", "Cost down but hardship_ok down 4 points on 300 paired cases."),
    ("hold", "Default gateway route upgraded without eval ticket."),
    ("ship", "Canary SLO met; two metrics up; latency flat."),
    ("hold", "Deprecation Friday; migration HOLD still open."),
    ("ship", "Sixty-day notice; HOLD cleared after latency fix."),
    ("hold", "Silent provider update behind fixed alias; canary flips 5/40."),
    ("ship", "Alias pinned to dated snapshot; repeats stable."),
    ("hold", "Judge revalidation skipped after model change."),
    ("ship", "Judge revalidated; TPR/TNR floors held."),
    ("hold", "Migration table mixed models mid-run; invalidate."),
    ("ship", "Clean single-model run log; deltas trusted."),
    ("hold", "Vendor bake-off without Harbor gold pins."),
    ("ship", "Harbor pins + paired delta table + HOLD rule followed."),
]
PROMPT = """Harbor gateway release review. Reply JSON only: {"verdict":"hold"|"ship","reason":"short"}\nCase:\n"""

def call(text):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=MODEL, max_tokens=80, messages=[{"role":"user","content": PROMPT+text}])
    raw = msg.content[0].text.strip(); a,b=raw.find("{"), raw.rfind("}")
    return json.loads(raw[a:b+1]) if a>=0 and b>a else {"raw": raw}

def main():
    live = "--live" in sys.argv
    if CACHE.exists() and not live:
        print(json.dumps({k:v for k,v in json.loads(CACHE.read_text()).items() if k!='rows'}, indent=2)); return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        CACHE.write_text(json.dumps({"status":"pending","n":0})); return
    rows=[]; correct=0
    for gold, desc in CASES:
        j=call(desc); pred=j.get("verdict"); ok=pred==gold; correct+=int(ok)
        rows.append({"gold":gold,"pred":pred,"ok":ok,"desc":desc[:70]}); time.sleep(0.12)
    out={"status":"ok","model":MODEL,"n":len(rows),"correct":correct,"accuracy":correct/len(rows),"rows":rows,"simulated_suite":True}
    CACHE.write_text(json.dumps(out, indent=2))
    print(json.dumps({k:out[k] for k in out if k!='rows'}, indent=2))

if __name__ == "__main__":
    main()
