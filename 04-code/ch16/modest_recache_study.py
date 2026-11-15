"""Modest NEW Anthropic study for Chapter 16 (2026-11-08).

Does NOT replace the historical full-lab OUTPUT (2,480 calls / n=200 claims).
Those remain [RESULT PENDING: full re-cache] until out/judge.jsonl etc. are rebuilt.

This script runs a stratified 24-trace subset (12 fail + 12 pass from the held-out
test set), generates replies, then scores reply-only / v0 / v1 with the small model.
Raw rows land in out/modest_study/ with model ids, tokens, latency, and ISO timestamps.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import fixture as F
import judges
import llm

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "modest_study"
IST = ZoneInfo("Asia/Calcutta")
N_FAIL = 12
N_PASS = 12
MODEL = llm.SMALL
RUN_ID = "ch16-modest-2026-11-08"
TAG_REPLIES = "modest_replies"
TAG_JUDGE = "modest_judge"


def select_traces():
    _, test = F.judge_set()
    fails = sorted([t for t in test if t["v11"] == "fail"], key=lambda t: t["trace_id"])[:N_FAIL]
    passes = sorted([t for t in test if t["v11"] == "pass"], key=lambda t: t["trace_id"])[:N_PASS]
    return fails + passes


def write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    # Key presence only — never print or write the secret
    import os
    if not (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        raise SystemExit("ANTHROPIC_API_KEY absent; modest study not run")

    started = datetime.now(IST)
    traces = select_traces()
    assert len(traces) == N_FAIL + N_PASS

    # --- replies ---
    reply_jobs = []
    for t in traces:
        prompt = __import__("gen").brief(t)
        reply_jobs.append((t["trace_id"], __import__("gen").req(prompt)))
    print(f"[{RUN_ID}] generating {len(reply_jobs)} replies with {MODEL} (live)")
    replies = llm.run(TAG_REPLIES, reply_jobs, live=True)
    missing = [i for i, _ in reply_jobs if i not in replies]
    if missing:
        raise SystemExit(f"reply cache incomplete: {len(missing)} missing (not printing ids list fully)")

    reply_rows = []
    for t in traces:
        rec = replies[t["trace_id"]]
        reply_rows.append({
            "run_id": RUN_ID,
            "started_ist": started.isoformat(),
            "trace_id": t["trace_id"],
            "kind": t["kind"],
            "v11": t["v11"],
            "stratum": t.get("stratum"),
            "model": rec.get("model"),
            "in_tokens": rec.get("in"),
            "out_tokens": rec.get("out"),
            "latency_s": rec.get("latency"),
            "stop": rec.get("stop"),
            "text": rec.get("text"),
            "key": rec.get("key"),
        })
    write_jsonl(OUT / "replies_raw.jsonl", reply_rows)

    # --- judges: j0, v0, v1 ---
    experiments = {
        "modest_j0": (judges.p_reply_only, "j0"),
        "modest_v0": (judges.p_v0, "v0"),
        "modest_v1": (judges.p_v1, "v1"),
    }
    all_judge_rows = []
    summaries = {}
    for exp_name, (prompt_fn, short) in experiments.items():
        jobs = []
        for t in traces:
            text = replies[t["trace_id"]]["text"]
            jobs.append((t["trace_id"], judges.req(prompt_fn(t, text), model=MODEL)))
        print(f"[{RUN_ID}] judging {exp_name} n={len(jobs)} live")
        scored = llm.run(TAG_JUDGE, jobs, live=True)
        tp = fp = tn = fn = abs_ = 0
        rows = []
        for t in traces:
            rec = scored.get(t["trace_id"])
            if not rec:
                continue
            verd = judges.verdict(rec["text"])
            gold = t["v11"]
            # abstain / cannot_tell counts as miss for positives, not FP for now
            if verd == "cannot_tell" or verd is None:
                abs_ += 1
                pred = "abstain"
            else:
                pred = verd
                if gold == "fail" and pred == "fail":
                    tp += 1
                elif gold == "pass" and pred == "pass":
                    tn += 1
                elif gold == "pass" and pred == "fail":
                    fp += 1
                elif gold == "fail" and pred == "pass":
                    fn += 1
            rows.append({
                "run_id": RUN_ID,
                "experiment": exp_name,
                "trace_id": t["trace_id"],
                "kind": t["kind"],
                "gold_v11": gold,
                "pred": pred,
                "model": rec.get("model"),
                "in_tokens": rec.get("in"),
                "out_tokens": rec.get("out"),
                "latency_s": rec.get("latency"),
                "stop": rec.get("stop"),
                "raw_text": rec.get("text"),
                "key": rec.get("key"),
            })
        all_judge_rows.extend(rows)
        n_pos = N_FAIL
        n_neg = N_PASS
        tpr = tp / n_pos if n_pos else None
        tnr = tn / n_neg if n_neg else None
        summaries[exp_name] = {
            "n": len(traces),
            "n_fail_gold": N_FAIL,
            "n_pass_gold": N_PASS,
            "tp": tp, "fn": fn, "fp": fp, "tn": tn, "abstain": abs_,
            "tpr": tpr, "tnr": tnr,
            "model": MODEL,
        }
        print(f"  {exp_name}: TPR {tp}/{n_pos} TNR {tn}/{n_neg} abstain {abs_}")

    write_jsonl(OUT / "judges_raw.jsonl", all_judge_rows)
    ended = datetime.now(IST)
    meta = {
        "run_id": RUN_ID,
        "label": "NEW modest study — not a recovery of missing full caches",
        "started_ist": started.isoformat(),
        "ended_ist": ended.isoformat(),
        "timezone": "Asia/Calcutta",
        "model_small": MODEL,
        "n_traces": len(traces),
        "selection": "12 fail + 12 pass from fee-judge-v1 test set, sorted by trace_id",
        "trace_ids": [t["trace_id"] for t in traces],
        "experiments": summaries,
        "raw_paths": {
            "replies": str(OUT / "replies_raw.jsonl"),
            "judges": str(OUT / "judges_raw.jsonl"),
            "llm_cache_replies": str(HERE / "out" / f"{TAG_REPLIES}.jsonl"),
            "llm_cache_judge": str(HERE / "out" / f"{TAG_JUDGE}.jsonl"),
        },
        "does_not_replace": [
            "historical OUTPUT.txt n=200 / 2480-call claims",
            "out/judge.jsonl full experiment matrix",
            "out/replies.jsonl full fixture replies",
        ],
        "chapter_policy": "Keep full-study numbers [RESULT PENDING: full re-cache]. Cite this run only as modest NEW evidence with n=24.",
    }
    (OUT / "summary.json").write_text(json.dumps(meta, indent=2) + "\n")
    # human-readable note
    lines = [
        f"# Chapter 16 modest re-cache study ({RUN_ID})",
        "",
        f"Started: {started.isoformat()} (Asia/Calcutta)",
        f"Ended: {ended.isoformat()} (Asia/Calcutta)",
        f"Model: {MODEL}",
        f"n={len(traces)} stratified (12 fail + 12 pass). **Not** equivalent to historical n=200 / 2,480-call study.",
        "",
        "Full historical caches remain missing; original chapter stats stay [RESULT PENDING: full re-cache].",
        "This directory holds genuine NEW raw responses only.",
        "",
        "## Results",
    ]
    for k, s in summaries.items():
        tpr_s = f"{s['tpr']:.3f}" if s['tpr'] is not None else "NA"
        tnr_s = f"{s['tnr']:.3f}" if s['tnr'] is not None else "NA"
        lines.append(
            f"- {k}: TPR {s['tp']}/{s['n_fail_gold']}={tpr_s} "
            f"TNR {s['tn']}/{s['n_pass_gold']}={tnr_s} "
            f"abstain={s['abstain']} (model {s['model']})"
        )
    lines += ["", "## Artefacts", f"- `{OUT / 'replies_raw.jsonl'}`", f"- `{OUT / 'judges_raw.jsonl'}`", f"- `{OUT / 'summary.json'}`", ""]
    (OUT / "README.md").write_text("\n".join(lines))
    print(f"[{RUN_ID}] wrote {OUT}")


if __name__ == "__main__":
    main()
