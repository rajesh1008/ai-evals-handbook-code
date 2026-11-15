"""Modest REAL Anthropic labels: is this review behaviour rubber-stamping?
Usage: python3 real_review_cue.py [--live]
Never prints the API key.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

OUT = Path(__file__).parent / "out"
CACHE = OUT / "real_review_cue.json"
MODEL = "claude-haiku-4-5-20251001"
CASES = [
    ("stamp", "Officer approved 40 of 40 offers in 4 seconds median; override rate 0%."),
    ("ok", "Officer overrode 7 of 40; median 32 seconds; cited policy twice."),
    ("stamp", "Approvals in under 5 seconds on 38/40; no comments."),
    ("ok", "Median 45 seconds; override 15%; flagged two income gaps."),
    ("stamp", "99.5% approval rate matching model; mean 3.2 seconds."),
    ("ok", "Disagreed with model on 6 hardship edges; slow on those."),
    ("bias", "Changed correct independent call to match wrong AI on 3 of 10 plants."),
    ("ok", "Blind condition matched gold on planted wrong AI offers."),
    ("stamp", "Same approval text pasted on 25 consecutive reviews."),
    ("bias", "Followed AI deferral that gold marks refuse; saw recommendation."),
    ("ok", "Second reviewer agreed with first on 18/20; times 20–60s."),
    ("stamp", "Override rate 0.4% on 250 reviews; p90 time 8 seconds."),
    ("ok", "Fatigue curve flat after break; late-bin agreement holds."),
    ("bias", "Under time pressure followed AI on 4 wrong plants."),
    ("ok", "Requested more docs instead of approving borderline offer."),
    ("stamp", "Zero overrides all week; chat shows streaming click-through."),
    ("ok", "Calibration session moved one officer closer to gold."),
    ("bias", "Anchored on AI fee waiver; gold says charge."),
    ("ok", "Escalated to senior when AI and policy notes conflicted."),
    ("stamp", "Approved while on phone; timestamps <2s apart for 15 items."),
    ("ok", "Wrote reason codes on every override."),
    ("bias", "Took AI hardship months despite gold prior-deferral block."),
    ("ok", "Post-review error 2/100 after sampling second review."),
    ("stamp", "Dashboard shows 99.2% approval; leadership celebrates."),
]

PROMPT = """You label Harbor hardship review behaviour.
Reply JSON only: {"kind":"stamp"|"bias"|"ok","reason":"short"}
Case:
"""

def call(text):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=MODEL, max_tokens=80, messages=[{"role":"user","content": PROMPT+text}])
    raw = msg.content[0].text.strip()
    a,b = raw.find("{"), raw.rfind("}")
    return json.loads(raw[a:b+1]) if a>=0 and b>a else {"raw": raw}

def main():
    live = "--live" in sys.argv
    if CACHE.exists() and not live:
        print(json.dumps({k:v for k,v in json.loads(CACHE.read_text()).items() if k!='rows'}, indent=2))
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        CACHE.write_text(json.dumps({"status":"pending","n":0}))
        return
    rows=[]; correct=0
    for gold, desc in CASES:
        j=call(desc)
        pred=j.get("kind")
        ok = pred == gold
        correct += int(ok)
        rows.append({"gold": gold, "pred": pred, "ok": ok, "desc": desc[:70]})
        time.sleep(0.12)
    out={"status":"ok","model":MODEL,"n":len(rows),"correct":correct,"accuracy":correct/len(rows),"rows":rows,"simulated_humans_in_lab":True}
    CACHE.write_text(json.dumps(out, indent=2))
    print(json.dumps({k:out[k] for k in out if k!='rows'}, indent=2))

if __name__ == "__main__":
    main()
