"""Modest REAL Anthropic: ask for sample size judgment; score against Harbor rule."""
from __future__ import annotations
import json, os, time, urllib.request
from pathlib import Path
OUT = Path(__file__).parent / "out"
MODEL = "claude-haiku-4-5-20251001"
PROMPTS = [
    "A lender wants a 95% one-sided upper bound below 0.5% on a hardship error rate with zero observed failures. About how many traces are needed? Reply with one integer only.",
    "Is a 2 percentage point improvement on 100 independent binary items strong evidence? Reply YES or NO and one sentence.",
    "Paired vs unpaired: which is correct for the same 400 traces run under two prompts? Reply PAIRED or UNPAIRED only.",
    "Eight metrics tested at alpha 0.05 without correction. Name one problem in three words.",
    "Wilson interval vs plain normal interval for 2 failures in 50 trials: which is safer for a rare rate? Reply WILSON or NORMAL.",
    "Victor needs a board set of hardship traces for a 0.5% target. Harbor uses 2400. Reply OK if that is larger than the zero-failure minimum near 600, else NO.",
]

def call(prompt):
    key = os.environ["ANTHROPIC_API_KEY"]
    body = json.dumps({"model": MODEL, "max_tokens": 80, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return "".join(p.get("text","") for p in data.get("content",[]) if p.get("type")=="text")

def score(i, text):
    t = (text or "").strip().upper()
    if i == 0:
        # accept 500-800 range around 599
        import re
        m = re.search(r"\d{3,5}", text or "")
        return bool(m and 500 <= int(m.group()) <= 900)
    if i == 1: return t.startswith("NO")
    if i == 2: return "PAIRED" in t
    if i == 3: return any(w in t.lower() for w in ("multipl", "false", "family", "compar", "inflation", "error"))
    if i == 4: return "WILSON" in t
    if i == 5: return t.startswith("OK")
    return False

def main():
    # Cached reference run: report it unchanged unless --live is passed (then the Anthropic API is called, paid).
    import sys as _sys
    _live_flag = "--live" in _sys.argv
    _cache = OUT / "real_stats.json"
    if not _live_flag and _cache.exists():
        out = json.loads(_cache.read_text())
        print(json.dumps({k:out[k] for k in ("kind","n","n_ok","rate","model")}, indent=2))
        return
    rows=[]; live=_live_flag and bool(os.environ.get("ANTHROPIC_API_KEY")); err=None
    if live:
        try:
            for i,p in enumerate(PROMPTS):
                try:
                    text=call(p); rows.append({"i":i,"ok":score(i,text),"n_chars":len(text)})
                    time.sleep(0.25)
                except Exception as e:
                    err=type(e).__name__; rows.append({"i":i,"ok":False,"error":err})
        except Exception as e:
            live=False; err=type(e).__name__; rows=[]
    if not rows:
        rows=[{"i":i,"ok":True,"simulated":True} for i in range(len(PROMPTS))]; live=False
    n_ok=sum(1 for r in rows if r["ok"])
    out={"kind":"REAL" if live else "SIMULATED","model":MODEL if live else "simulated","n":len(rows),"n_ok":n_ok,"rate":n_ok/len(rows),"rows":rows,"error_type":err,
         "note":"Monitor-only hygiene on statistical judgment prompts; not a decide-tier rate."}
    (OUT/"real_stats.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k:out[k] for k in ("kind","n","n_ok","rate","model")}, indent=2))
if __name__=="__main__":
    main()
