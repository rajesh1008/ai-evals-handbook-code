"""Live Anthropic groundedness judgements on a modest sample.

Usage:
  python3 real_grounding.py run     # needs ANTHROPIC_API_KEY
  python3 real_grounding.py report  # print cached out/real_grounding.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import CORPUS
from fixture import build_gold, rankings_for_index, RANK_SEED
from corpus import live_chunk_ids

OUT = Path(__file__).resolve().parent / "out" / "real_grounding.json"
MODEL = "claude-haiku-4-5-20251001"
N = 24  # modest sample


def _client():
    import anthropic
    return anthropic.Anthropic()


def judge_one(client, claim: str, passages: list[str]) -> dict:
    prompt = (
        "You judge whether the CLAIM is supported by the PASSAGES.\n"
        "Reply with exactly one line: SUPPORTED or UNSUPPORTED, then a short reason.\n\n"
        f"CLAIM:\n{claim}\n\nPASSAGES:\n"
        + "\n---\n".join(passages)
    )
    t0 = time.time()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=80,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if hasattr(b, "text"))
    supported = text.strip().upper().startswith("SUPPORTED")
    return {
        "supported": supported,
        "text": text.strip(),
        "in_tokens": msg.usage.input_tokens,
        "out_tokens": msg.usage.output_tokens,
        "seconds": time.time() - t0,
    }


def run():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY unset; not running")
        return 2
    gold = build_gold(90)[:N]
    rank = rankings_for_index(gold, live_chunk_ids(), noise=0.40, seed=RANK_SEED)
    claim_map = {
        "grace": "The grace period is fifteen days before a late fee.",
        "amount": "The late fee is twenty-five dollars.",
        "waiver": "Autopay borrowers get one courtesy waiver in twelve months.",
        "returned": "A returned payment fee is fifteen dollars.",
        "window": "Hardship is once in twelve calendar months.",
        "income": "Income must be confirmed before drafting a hardship offer.",
        "eligibility": "Medical expense spikes can make a borrower hardship eligible.",
        "timing": "Lien release is requested within five business days after payoff.",
        "letter": "A payoff letter includes the good-through date and per-diem.",
        "history": "Compass can send statements for the most recent twenty-four months.",
    }
    client = _client()
    rows = []
    tin = tout = 0
    for g in gold:
        rel = next(iter(g["relevant"]))
        section = rel.split("::")[1]
        claim = claim_map[section]
        passages = [CORPUS[cid]["text"] for cid in rank[g["query_id"]][:3]]
        j = judge_one(client, claim, passages)
        tin += j["in_tokens"]
        tout += j["out_tokens"]
        rows.append({"query_id": g["query_id"], "claim": claim, "relevant": rel, **j})
        print(f"  {g['query_id']} supported={j['supported']} {j['text'][:60]}")
    supported = sum(1 for r in rows if r["supported"])
    out = {
        "model": MODEL,
        "n": N,
        "supported": supported,
        "rate": supported / N,
        "input_tokens": tin,
        "output_tokens": tout,
        "approx_usd": tin / 1e6 * 1.0 + tout / 1e6 * 5.0,
        "rows": rows,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}; {supported}/{N} supported; ~${out['approx_usd']:.3f}")
    return 0


def report():
    if not OUT.exists():
        print("no cache at", OUT)
        return 1
    data = json.loads(OUT.read_text())
    print(json.dumps({k: data[k] for k in data if k != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    raise SystemExit(run() if cmd == "run" else report())
