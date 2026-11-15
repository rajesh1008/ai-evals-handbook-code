"""Modest REAL Anthropic hygiene on live-experiment prompts; monitor-only."""
from __future__ import annotations
import json, os, urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "out"
MODEL = "claude-haiku-4-5-20251001"
PROMPTS = [
    "Name one safe unit of randomisation for a lending chatbot A/B test in one sentence.",
    "What is a guardrail metric in an online experiment? One sentence.",
    "Why can peeking at A/B results without alpha spending mislead? One sentence.",
    "What is interleaving for retrieval ranking evaluation? One sentence.",
    "State one ethics concern when experimenting on hardship borrowers. One sentence.",
    "Should a holiday-weekend error spike stop an experiment arm? Answer yes or no and why in one sentence.",
]

def call(prompt: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 120,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    texts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    return "\n".join(texts).strip()

def score(ans: str) -> bool:
    return len(ans.split()) >= 6 and len(ans) < 600

def main():
    # Cached reference run: report it unchanged unless --live is passed (then the Anthropic API is called, paid).
    import sys as _sys
    _live_flag = "--live" in _sys.argv
    _cache = OUT / "real_ab.json"
    if not _live_flag and _cache.exists():
        out = json.loads(_cache.read_text())
        print(json.dumps({k: out[k] for k in ("kind", "n", "n_ok", "rate", "error_type", "note")}))
        return
    if not _live_flag:
        print("no cached run at out/real_ab.json and --live not given; not calling the API (see OUTPUT.txt)")
        return
    rows = []
    n_ok = 0
    err = None
    try:
        for i, p in enumerate(PROMPTS):
            ans = call(p)
            ok = score(ans)
            n_ok += int(ok)
            rows.append({"i": i, "ok": ok, "n": len(ans.split())})
    except Exception as e:
        err = type(e).__name__
    out = {
        "kind": "REAL",
        "model": MODEL,
        "n": len(PROMPTS),
        "n_ok": n_ok,
        "rate": n_ok / len(PROMPTS),
        "rows": rows,
        "error_type": err,
        "note": "monitor-only",
    }
    (OUT / "real_ab.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("kind", "n", "n_ok", "rate", "error_type", "note")}))

if __name__ == "__main__":
    main()
