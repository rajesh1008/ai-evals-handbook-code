"""Modest REAL Anthropic: classify noise-floor gate cues.
Usage: python3 real_repeat_cue.py [--live]
Never prints API key.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
OUT = Path(__file__).parent / "out"
CACHE = OUT / "real_repeat_cue.json"
MODEL = "claude-haiku-4-5-20251001"
CASES = [
    ("noise", "Hardship mean 88.2; candidate 87.5; published floor 1.4; margin 0.5."),
    ("regression", "Hardship mean 88.2; candidate 85.0; floor 1.4; margin 0.5."),
    ("noise", "Fee 91.0 to 90.3; floor 1.4; margin 0.5."),
    ("regression", "Fee 91.0 to 88.0; floor 1.4; margin 0.5."),
    ("noise", "Two runs differ by 0.9 pts; floor 1.4."),
    ("improvement", "Hardship 88.2 to 91.0; floor 1.4; margin 0.5."),
    ("noise", "pass@3 0.80 but pass^3 0.20 on same trials — report both, not a ship call."),
    ("regression", "Five-run mean drop 2.6 pts vs baseline; floor 1.4; margin 0.5."),
    ("noise", "Temperature 0 still flipped 2 of 24 canaries; treat as floor, not product bug."),
    ("regression", "Silent prompt date change; hardship -3.1 pts; floor 1.4."),
    ("noise", "Inside-floor injection drop 0.8 pts; naive gate alarmed."),
    ("noise", "Run scores 87.1, 88.4, 87.9, 88.8, 87.6; half-range under 1.4."),
    ("regression", "Candidate tool schema change; fee -2.4 pts; floor 1.4; margin 0.5."),
    ("improvement", "After pin fix; hardship +2.2 pts above floor+margin."),
    ("noise", "Judge flip rate matches production rerun floor."),
    ("regression", "Gateway mid-run upgrade; hardship -2.8 pts."),
    ("noise", "Seed unset but |delta| 0.4 pts."),
    ("noise", "Retry with contaminated context; do not inflate pass@k."),
    ("regression", "Published floor ignored; product ship on -2.1 pts."),
    ("noise", "Report mean of five runs; single-run leaderboard refused."),
    ("improvement", "Margin cleared; +2.0 pts after eval ticket."),
    ("noise", "Formatting-only prompt tweak; score jitter 0.6 pts."),
    ("regression", "Batching change moved hardship -3.5 pts."),
    ("noise", "Which of two runs is right? Neither alone — publish floor."),
]
PROMPT = """Harbor noise-floor review. Reply JSON only: {"verdict":"noise"|"regression"|"improvement","reason":"short"}\nCase:\n"""

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
