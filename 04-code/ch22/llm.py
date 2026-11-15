"""Cached model calls for the Chapter 22 lab. Every call is keyed by a digest of its full request
and stored in out/<tag>.jsonl with tokens and wall-clock latency, so analyses rerun without a key.
The key is read by the SDK from ANTHROPIC_API_KEY and never printed or stored."""
import concurrent.futures as cf
import hashlib
import json
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
SMALL = "claude-haiku-4-5-20251001"
LARGE = "claude-sonnet-4-5-20250929"
# Illustrative list prices per million tokens (US dollars), as assumed in the chapter [VERIFY 2026-11-01].
PRICE = {SMALL: (1.00, 5.00), LARGE: (3.00, 15.00)}


def key_of(req):
    return hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()[:16]


def load(tag):
    p = OUT / f"{tag}.jsonl"
    if not p.exists():
        return {}
    return {r["key"]: r for r in map(json.loads, p.read_text().splitlines()) if r.get("text") is not None}


def _call(req):
    import anthropic
    client = anthropic.Anthropic(max_retries=8)
    t0 = time.perf_counter()
    msg = client.messages.create(**req)
    dt = time.perf_counter() - t0
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    return {"text": text, "model": msg.model, "in": msg.usage.input_tokens, "out": msg.usage.output_tokens,
            "latency": round(dt, 3), "stop": msg.stop_reason}


def run(tag, jobs, live=False, workers=8):
    """jobs: list of (item_id, req). Returns {item_id: record}. Calls the API only when live is True."""
    cache = load(tag)
    todo = [(i, r) for i, r in jobs if key_of(r) not in cache]
    if todo and live:
        print(f"  [{tag}] calling the model for {len(todo)} uncached requests")
        with (OUT / f"{tag}.jsonl").open("a") as fh, cf.ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(_call, r): (i, r) for i, r in todo}
            for f in cf.as_completed(futs):
                i, r = futs[f]
                try:
                    rec = f.result()
                except Exception as e:  # recorded so a rerun retries it
                    print(f"  [{tag}] {i}: {type(e).__name__}")
                    continue
                rec.update({"key": key_of(r), "item": i})
                fh.write(json.dumps(rec) + "\n"); fh.flush()
        cache = load(tag)
    return {i: cache[key_of(r)] for i, r in jobs if key_of(r) in cache}


def cost(rec):
    pin, pout = PRICE[rec["model"]]
    return (rec["in"] * pin + rec["out"] * pout) / 1e6


def usage(recs):
    recs = list(recs)
    return {"calls": len(recs), "in": sum(r["in"] for r in recs), "out": sum(r["out"] for r in recs),
            "cost": sum(cost(r) for r in recs)}
