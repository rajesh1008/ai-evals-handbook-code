"""Modest REAL Anthropic judgments on degraded stub *descriptions* (text stand-ins for photos).

Usage: python3 real_vision.py [--live]
Never prints the API key.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

OUT = Path(__file__).parent / "out"
CACHE = OUT / "real_vision.json"
MODEL = "claude-haiku-4-5-20251001"

CASES = [
    ("clean", "Pay stub photo: clear text GROSS 2410.00 NET 1888.50 DEDUCTION -45.00"),
    ("glare", "Pay stub photo: glare band over net; visible GROSS 2410.00 NET #### DEDUCTION -45.00"),
    ("blur", "Pay stub photo: motion blur; GROSS looks 2410 or 2470; NET unreadable"),
    ("crop", "Pay stub photo: right edge cropped; GROSS 2410.00 NET missing; employer Desert Ridge"),
    ("skew", "Pay stub photo: skewed 25 deg; OCR candidate NET 1888.50 vs 188850"),
    ("compression", "Pay stub photo: heavy JPEG blocks; DEDUCTION may read 45.00 without minus"),
    ("clean", "PDF upload: structured fields gross=1900.00 net=1402.25 deduction=-88.10"),
    ("glare", "Car-cabin photo of stub; dashboard reflection; period_end smudged"),
    ("blur", "Dealer lot photo; wind flap; ytd_gross uncertain"),
    ("crop", "Thumb over net amount; gross clear"),
    ("skew", "Phone angle; columns misaligned; employer Camelback Motors"),
    ("compression", "WhatsApp recompress; minus sign on deduction gone"),
    ("clean", "Clear scan deduction -120.00 must stay negative"),
    ("glare", "Streetlight glare on net line"),
    ("blur", "Low light indoor blur on period_end"),
    ("crop", "Bottom cropped losing ytd"),
    ("skew", "Rotated almost 90 degrees"),
    ("compression", "Twice-compressed MMS image"),
    ("clean", "PDF digital original no photo noise"),
    ("glare", "Plastic sleeve shine"),
    ("blur", "Walking while photographing"),
    ("crop", "Only left half of stub"),
    ("skew", "Perspective warp from lap photo"),
    ("compression", "Email attachment downscale"),
]

PROMPT = """You label a hardship pay-stub image DESCRIPTION for Harbor evals.
Reply JSON only: {"layer_fail":"none"|"capture"|"recognition"|"interpretation","minus_preserved":true|false,"confidence":0-1}
Description:
"""

def call(text):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=MODEL, max_tokens=100, messages=[{"role":"user","content": PROMPT+text}])
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
    rows=[]
    for level, desc in CASES:
        j = call(desc)
        j["level"]=level
        j["desc"]=desc[:70]
        rows.append(j)
        time.sleep(0.12)
    minus_ok = sum(1 for r in rows if r.get("minus_preserved") is True)
    out={"status":"ok","model":MODEL,"n":len(rows),"minus_preserved_n":minus_ok,"rows":rows}
    CACHE.write_text(json.dumps(out, indent=2))
    print(json.dumps({k:out[k] for k in out if k!='rows'}, indent=2))

if __name__ == "__main__":
    main()
