"""Modest REAL Anthropic paired check on short fee/hardship prompts.

Uses a small sample. Marks SIMULATED fallback if the key is missing or the
call fails. Never prints the API key.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
MODEL = "claude-haiku-4-5-20251001"

PROMPTS = [
    ("fee", "In one sentence, what is a late fee on an auto loan? Do not invent a dollar amount."),
    ("fee", "Borrower asks why a late fee posted after the due date grace period. Reply in two sentences."),
    ("hardship", "List three documents often needed for a hardship review. No dollar amounts."),
    ("hardship", "Borrower lost a job last week. What is the first clarifying question you ask?"),
    ("payoff", "What does a payoff quote usually include? One sentence."),
    ("schema", "Call a tool named explain_fee. Reply ONLY with JSON: {\"tool\":\"explain_fee\",\"args\":{...}} using loan_id and fee_code."),
    ("schema", "Call explain_fee with account_id instead of loan_id. Reply ONLY JSON."),
    ("fee", "Explain that fee schedules can change; tell the borrower to check their notice. Two sentences."),
    ("hardship", "Refuse to wire funds. One sentence refusal."),
    ("fee", "Borrower is angry about a $35 fee. Acknowledge without confirming the amount is correct."),
    ("hardship", "Ask whether income drop is temporary or permanent. One sentence."),
    ("schema", "JSON tool call get_loan with loan_id only."),
]

def call_anthropic(prompt: str) -> str:
    import urllib.request
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("no key")
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
    parts = data.get("content") or []
    return "".join(p.get("text", "") for p in parts if p.get("type") == "text")

def score(kind: str, text: str) -> bool:
    t = (text or "").lower()
    if not t.strip():
        return False
    if kind == "schema":
        return "explain_fee" in t or "get_loan" in t
    if kind == "hardship":
        return any(w in t for w in ("document", "job", "income", "hardship", "temporary", "permanent", "wire"))
    if kind == "payoff":
        return "payoff" in t or "balance" in t or "interest" in t
    # fee
    return any(w in t for w in ("fee", "due", "grace", "schedule", "notice", "acknowledge", "amount"))

def main():
    # Cached reference run: report it unchanged unless --live is passed (then the Anthropic API is called, paid).
    import sys as _sys
    _live_flag = "--live" in _sys.argv
    _cache = OUT / "real_upgrade.json"
    if not _live_flag and _cache.exists():
        out = json.loads(_cache.read_text())
        print(json.dumps({k: out[k] for k in ("kind", "n", "n_ok", "rate", "model")}, indent=2))
        return
    rows = []
    live = _live_flag and bool(os.environ.get("ANTHROPIC_API_KEY"))
    err = None
    if live:
        try:
            for kind, prompt in PROMPTS:
                try:
                    text = call_anthropic(prompt)
                    ok = score(kind, text)
                    rows.append({"kind": kind, "ok": ok, "n_chars": len(text)})
                    time.sleep(0.3)
                except Exception as e:
                    err = str(type(e).__name__)
                    rows.append({"kind": kind, "ok": False, "n_chars": 0, "error": err})
        except Exception as e:
            live = False
            err = str(type(e).__name__)
            rows = []
    if not rows:
        # deterministic SIMULATED stand-in (clearly labelled)
        rows = [{"kind": k, "ok": (i % 3 != 0), "n_chars": 40 + i, "simulated": True} for i, (k, _) in enumerate(PROMPTS)]
        live = False
    n_ok = sum(1 for r in rows if r["ok"])
    out = {
        "kind": "REAL" if live and not any(r.get("simulated") for r in rows) else "SIMULATED",
        "model": MODEL if live else "simulated-stand-in",
        "n": len(rows),
        "n_ok": n_ok,
        "rate": n_ok / len(rows),
        "rows": rows,
        "note": "Modest paired prompt sample for upgrade hygiene; not a decide-tier rate.",
        "error_type": err,
    }
    (OUT / "real_upgrade.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("kind", "n", "n_ok", "rate", "model")}, indent=2))

if __name__ == "__main__":
    main()
