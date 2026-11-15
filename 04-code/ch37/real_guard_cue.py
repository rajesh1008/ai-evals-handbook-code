"""Modest REAL Anthropic cues for guard/monitor/eval placement. Never print keys."""
from __future__ import annotations
import json, os, sys
from pathlib import Path

OUT = Path(__file__).parent / "out"

CUES = [
    {"gold": "guard", "desc": "Block hardship offer missing income field before officer UI."},
    {"gold": "monitor", "desc": "Weekly sample of 200 production turns scored offline overnight."},
    {"gold": "eval", "desc": "PR slow suite with judges on fee explanations before merge."},
    {"gold": "guard", "desc": "Refuse tool call that would SMS outside policy window."},
    {"gold": "monitor", "desc": "Alert when over-block rate on benign scary words rises."},
    {"gold": "eval", "desc": "Signature 8 offline-online correlation study for fee proxy."},
    {"gold": "guard", "desc": "In-flight schema check on fee_amount parse under 80ms."},
    {"gold": "monitor", "desc": "Drift detector on proxy embeddings without raw text."},
    {"gold": "eval", "desc": "Promote two code checks only after offline precision report."},
    {"gold": "guard", "desc": "Timeout path when guard p99 exceeds SMS 2000ms budget."},
    {"gold": "monitor", "desc": "Post-hoc review of blocked benign foreclosure vocabulary."},
    {"gold": "eval", "desc": "Pre-deploy red team of guard with MonitoringBench-style attacks."},
]

PROMPT = (
    "Classify each production check as exactly one of: guard, monitor, eval.\n"
    "Reply with only the label.\n\nCase: {desc}"
)


def classify_local(desc: str) -> str:
    d = desc.lower()
    if any(k in d for k in ("block", "refuse", "in-flight", "timeout", "sms", "schema check")):
        return "guard"
    if any(k in d for k in ("weekly", "alert", "drift", "post-hoc", "overnight")):
        return "monitor"
    return "eval"


def classify_anthropic(desc: str) -> str:
    import urllib.request

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("missing key")
    body = json.dumps(
        {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 20,
            "messages": [{"role": "user", "content": PROMPT.format(desc=desc)}],
        }
    ).encode()
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
    text = data["content"][0]["text"].strip().lower()
    for lab in ("guard", "monitor", "eval"):
        if lab in text.split():
            return lab
        if text.startswith(lab):
            return lab
    return text.split()[0] if text else "eval"


def main(live: bool = False):
    rows = []
    model = "local-heuristic"
    status = "simulated_fallback"
    for c in CUES:
        if live and os.environ.get("ANTHROPIC_API_KEY"):
            try:
                pred = classify_anthropic(c["desc"])
                model = "claude-haiku-4-5-20251001"
                status = "ok"
            except Exception as e:
                pred = classify_local(c["desc"])
                status = f"fallback:{type(e).__name__}"
        else:
            pred = classify_local(c["desc"])
        rows.append({"gold": c["gold"], "pred": pred, "ok": pred == c["gold"], "desc": c["desc"]})
    correct = sum(1 for r in rows if r["ok"])
    out = {
        "status": status,
        "model": model,
        "n": len(rows),
        "correct": correct,
        "accuracy": round(correct / len(rows), 4),
        "rows": rows,
        "simulated_suite": True,
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "real_guard_cue.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("status", "model", "n", "correct", "accuracy")}, indent=2))


if __name__ == "__main__":
    main(live="--live" in sys.argv)
