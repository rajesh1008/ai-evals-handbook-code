#!/usr/bin/env python3
"""Derive NEW result report from raw caches + ledger. No API calls."""
from __future__ import annotations
import json, os, sys
from collections import Counter
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
CH16 = RUN_DIR.parents[1]
sys.path.insert(0, str(CH16))
os.environ.setdefault("CH16_OUT", str(RUN_DIR / "out"))

import llm
import gen
import judges as J
import fixture as F
import budget as B

OUT = Path(os.environ["CH16_OUT"])


def load_tag(tag):
    p = OUT / f"{tag}.jsonl"
    if not p.exists():
        return {}
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    # last wins by key or item
    by = {}
    for r in rows:
        by[r.get("key") or r.get("item")] = r
    return by


def score_exp(name, traces, res):
    # mirror judges.verdict + common.score lightly
    tp = tn = fp = fn = 0
    preds = {}
    for t in traces:
        tid = t["trace_id"]
        if tid not in res:
            continue
        pred = J.verdict(res[tid]["text"])
        preds[tid] = pred
        gold = t["v11"]
        if gold == "fail" and pred == "fail":
            tp += 1
        elif gold == "pass" and pred == "pass":
            tn += 1
        elif gold == "pass" and pred == "fail":
            fp += 1
        elif gold == "fail" and pred == "pass":
            fn += 1
    tpr = tp / (tp + fn) if (tp + fn) else None
    tnr = tn / (tn + fp) if (tn + fp) else None
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "tpr": tpr, "tnr": tnr, "n": len(preds),
            "verdicts": dict(Counter(preds.values()))}


def main():
    os.environ.setdefault("CH16_BUDGET_CAP", "12")
    os.environ.setdefault("CH16_BUDGET_LEDGER", str(RUN_DIR / "budget_ledger.json"))
    B.reset_ledger_singleton_for_tests()
    rem = B.get_ledger().remaining_cap() if (RUN_DIR / "budget_ledger.json").exists() else {}

    report = {
        "run_id": os.environ.get("CH16_RUN_ID", RUN_DIR.name),
        "note": "NEW experiment — not recovered historical",
        "budget": rem,
        "files": {p.name: p.stat().st_size for p in sorted(OUT.glob('*.jsonl'))},
        "counts": {p.stem: sum(1 for _ in p.open() if _.strip()) for p in sorted(OUT.glob('*.jsonl'))},
    }

    # usage per file
    usage = {}
    for p in sorted(OUT.glob("*.jsonl")):
        recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip() and '"in"' in l]
        if recs and "in" in recs[0]:
            usage[p.stem] = llm.usage(recs)
    report["usage_by_file"] = usage
    report["usage_total"] = {
        "calls": sum(u["calls"] for u in usage.values()),
        "in": sum(u["in"] for u in usage.values()),
        "out": sum(u["out"] for u in usage.values()),
        "cost": sum(u["cost"] for u in usage.values()),
    }

    # Judge metrics if present
    try:
        res_all = J.load_all(live=False)
        dev, test = F.judge_set()
        metrics = {}
        for name in ("test_j0", "test_v0", "test_v1_small_r0", "test_v1_large", "test_v1_think",
                     "test_verdict_only", "test_tone", "test_v1_spanish"):
            if name in res_all and res_all[name]:
                traces = test
                if "spanish" in name:
                    ids = set(gen.spanish_ids())
                    traces = [t for t in test if t["trace_id"] in ids]
                metrics[name] = score_exp(name, traces, res_all[name])
        report["judge_metrics"] = metrics
    except Exception as e:
        report["judge_metrics_error"] = f"{type(e).__name__}: {e}"

    # Agent summary
    agent_sum = {}
    for tag in ("agent_small", "agent_large", "agent_small_calc"):
        p = OUT / f"{tag}.jsonl"
        if not p.exists():
            continue
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        agent_sum[tag] = {
            "n": len(rows),
            "tools": sum(len(r.get("tool_calls") or []) for r in rows),
            "usage": llm.usage(rows) if rows else {},
            "mean_latency": sum(r.get("latency") or 0 for r in rows) / max(len(rows), 1),
        }
    report["agent"] = agent_sum

    outp = RUN_DIR / "reports" / "NEW_RESULTS.json"
    outp.write_text(json.dumps(report, indent=2) + "\n")
    md = RUN_DIR / "reports" / "NEW_RESULTS.md"
    lines = [
        f"# NEW Ch16 results — {report['run_id']}",
        "",
        "**NEW experiment, not recovered historical.**",
        "",
        f"Budget: `{json.dumps(rem)}`",
        f"Usage total: `{json.dumps(report['usage_total'])}`",
        f"Files: `{json.dumps(report['counts'])}`",
        "",
        "## Judge metrics (from NEW raw caches)",
        "```json",
        json.dumps(report.get("judge_metrics", {}), indent=2),
        "```",
        "",
        "## Agent",
        "```json",
        json.dumps(agent_sum, indent=2),
        "```",
        "",
    ]
    md.write_text("\n".join(lines))
    print(f"wrote {outp}")
    print(f"wrote {md}")
    print("budget", rem)
    print("usage_total", report["usage_total"])


if __name__ == "__main__":
    main()
