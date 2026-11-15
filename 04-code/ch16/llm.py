"""Cached model calls for the Chapter 16 lab. Every call is keyed by a digest of its full request
and stored in out/<tag>.jsonl with tokens and wall-clock latency, so analyses rerun without a key.
The key is read by the SDK from ANTHROPIC_API_KEY and never printed or stored.

When CH16_BUDGET_CAP is set, every live messages.create goes through budget.py: reserve worst-case
USD before dispatch, commit actual after, no unbounded SDK retries, unpriced models refused.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import time
from pathlib import Path

import budget as B

OUT = Path(os.environ["CH16_OUT"]) if os.environ.get("CH16_OUT") else Path(__file__).resolve().parent / "out"
SMALL = "claude-haiku-4-5-20251001"
LARGE = "claude-sonnet-4-5-20250929"
# Verified list prices per million tokens (US dollars) — must match budget.PRICE.
PRICE = {SMALL: (1.00, 5.00), LARGE: (3.00, 15.00)}


def key_of(req):
    return hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()[:16]


def load(tag):
    p = OUT / f"{tag}.jsonl"
    if not p.exists():
        return {}
    return {r["key"]: r for r in map(json.loads, p.read_text().splitlines()) if r.get("text") is not None}


def _sanitize_req(req: dict) -> dict:
    """Persistable request copy — never includes secrets (key is env-only)."""
    return json.loads(json.dumps(req, sort_keys=True))


def _call(req, tag=None, item=None):
    """One Messages API create. Budget-guarded when CH16_BUDGET_CAP is set."""
    import anthropic

    B.assert_model_priced(req["model"])
    rid = None
    if B.enabled():
        worst = B.worst_case_usd(req)
        rid = B.get_ledger().reserve(worst, meta={"tag": tag, "item": item, "model": req["model"],
                                                   "max_tokens": req.get("max_tokens"),
                                                   "worst_usd": worst})
    # No automatic unbounded SDK retries — each retry must re-reserve.
    client = anthropic.Anthropic(max_retries=0, timeout=180.0)
    t0 = time.perf_counter()
    try:
        msg = client.messages.create(**req)
    except Exception as e:
        if rid is not None:
            # Unknown whether the provider charged — keep reservation until reconciled.
            name = type(e).__name__
            if name in ("APIConnectionError", "APITimeoutError", "TimeoutError", "ReadTimeout", "APITimeoutError") or "timeout" in str(e).lower() or "connection" in str(e).lower():
                # Likely uncharged; release.
                B.get_ledger().release(rid, reason=f"likely_uncharged:{name}")
            else:
                B.get_ledger().mark_unreconciled(rid, f"{name}: {e}")
        raise
    dt = time.perf_counter() - t0
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    tin = int(msg.usage.input_tokens)
    tout = int(msg.usage.output_tokens)
    # thinking tokens (if any) appear in usage output for this API shape
    actual = B.guarded_cost_usd(msg.model, tin, tout)
    if rid is not None:
        B.get_ledger().commit(rid, actual)
    rec = {
        "text": text,
        "model": msg.model,
        "in": tin,
        "out": tout,
        "latency": round(dt, 3),
        "stop": msg.stop_reason,
        "request_id": getattr(msg, "id", None),
        "cost_usd": actual,
        "req_digest": key_of(req),
        "req": _sanitize_req(req),
    }
    return rec


def run(tag, jobs, live=False, workers=4):
    """jobs: list of (item_id, req). Returns {item_id: record}. Calls the API only when live is True."""
    OUT.mkdir(parents=True, exist_ok=True)
    cache = load(tag)
    todo = [(i, r) for i, r in jobs if key_of(r) not in cache]
    if todo and live:
        print(f"  [{tag}] calling the model for {len(todo)} uncached requests")
        with (OUT / f"{tag}.jsonl").open("a") as fh, cf.ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(_call, r, tag, i): (i, r) for i, r in todo}
            for f in cf.as_completed(futs):
                i, r = futs[f]
                try:
                    rec = f.result()
                except B.BudgetExhausted as e:
                    print(f"  [{tag}] BUDGET STOP: {e}")
                    # Cancel remaining futures best-effort
                    for other in futs:
                        other.cancel()
                    # Drain in-flight that already reserved
                    for other in futs:
                        if other is f:
                            continue
                        try:
                            other.result(timeout=0.01)
                        except Exception:
                            pass
                    raise
                except Exception as e:  # recorded so a rerun retries it
                    print(f"  [{tag}] {i}: {type(e).__name__}: {e}")
                    continue
                rec.update({"key": key_of(r), "item": i})
                fh.write(json.dumps(rec) + "\n"); fh.flush()
        cache = load(tag)
    elif todo and not live:
        pass  # cache miss offline — omit
    return {i: cache[key_of(r)] for i, r in jobs if key_of(r) in cache}


def cost(rec):
    pin, pout = PRICE[rec["model"]]
    return (rec["in"] * pin + rec["out"] * pout) / 1e6


def usage(recs):
    recs = list(recs)
    return {"calls": len(recs), "in": sum(r["in"] for r in recs), "out": sum(r["out"] for r in recs),
            "cost": sum(cost(r) for r in recs)}
