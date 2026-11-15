"""Modest REAL Anthropic trajectory-judge sample for Chapter 24.

Scores a sample of trajectories as process-correct or not. Traffic and planted
truth are SIMULATED; judge verdicts are real model output when ANTHROPIC_API_KEY
is set. Cached under out/judge/. Never prints the key.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

OUT = Path(__file__).parent / "out"
CACHE = OUT / "judge"
CACHE.mkdir(parents=True, exist_ok=True)
FIX = json.loads((OUT / "fixture.json").read_text())

MODEL = "claude-haiku-4-5-20251001"
SAMPLE_N = 40  # modest
PRICE_IN = 1.0 / 1e6   # assumed $1/M in
PRICE_OUT = 5.0 / 1e6  # assumed $5/M out


def render_traj(t: dict) -> str:
    lines = [f"trace_id={t['trace_id']} action={t['action']}"]
    for i, s in enumerate(t["steps"], 1):
        lines.append(f"{i}. tool={s['tool']} status={s['status']} args={json.dumps(s['args'], sort_keys=True)}")
    return "\n".join(lines)


SYSTEM = (
    "You are a trajectory judge for a lending hardship assistant. "
    "A correct process must: look up the loan, look up the borrower, look up hardship policy, "
    "check eligibility with loan_id and reason, then either draft_offer or refer_officer. "
    "Guessing a plan via compute_plan without check_eligibility is a process failure even if "
    "the offer looks right. Reply with exactly two lines:\n"
    "VERDICT: pass|fail\n"
    "REASON: one short sentence."
)


def pick_sample(seed=2026):
    import random
    rng = random.Random(seed)
    # Stratify: 15 lucky + 5 missing_elig + 5 wrong_offer + 15 clean (process-correct)
    by = {}
    for t in FIX["trajectories"]:
        by.setdefault(t["kind"], []).append(t)
    sample = []
    lucky = list(by.get("lucky", [])); rng.shuffle(lucky)
    sample += lucky[:15]
    sample += by.get("missing_elig", [])[:5]
    sample += by.get("wrong_offer", [])[:5]
    clean = list(by.get("clean", [])); rng.shuffle(clean)
    sample += clean[:15]
    # Prefer named lucky-pass in the sample
    named = next((t for t in FIX["trajectories"] if t["trace_id"] == "t-270087"), None)
    if named and named not in sample:
        sample[0] = named
    return sample[:SAMPLE_N]


def call_one(client, t):
    path = CACHE / f"{t['trace_id']}.json"
    if path.exists():
        return json.loads(path.read_text())
    msg = client.messages.create(
        model=MODEL,
        max_tokens=80,
        system=SYSTEM,
        messages=[{"role": "user", "content": render_traj(t)}],
    )
    text = msg.content[0].text
    usage = {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}
    rec = {"trace_id": t["trace_id"], "text": text, "usage": usage,
           "planted_process_ok": t["process_ok"], "fixture_kind": t["kind"]}
    path.write_text(json.dumps(rec))
    return rec


def parse_verdict(text: str) -> str:
    for line in text.splitlines():
        if line.upper().startswith("VERDICT"):
            v = line.split(":", 1)[-1].strip().lower()
            if "pass" in v and "fail" not in v:
                return "pass"
            if "fail" in v:
                return "fail"
    low = text.lower()
    if "fail" in low:
        return "fail"
    if "pass" in low:
        return "pass"
    return "unclear"


def main(live: bool):
    sample = pick_sample()
    print(f"sample {len(sample)}; cache dir {CACHE}")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if live and not key:
        print("ANTHROPIC_API_KEY not set; writing pending marker")
        (OUT / "judge_pending.json").write_text(json.dumps({
            "status": "pending", "command": "python3 real_judge.py --live",
            "n": len(sample),
        }))
        return
    if not live:
        # score from cache only
        recs = []
        missing = []
        for t in sample:
            path = CACHE / f"{t['trace_id']}.json"
            if path.exists():
                recs.append(json.loads(path.read_text()))
            else:
                missing.append(t["trace_id"])
        if missing:
            print(f"missing cache for {len(missing)}; run with --live")
            (OUT / "judge_pending.json").write_text(json.dumps({
                "status": "pending", "missing": missing[:10], "n_missing": len(missing),
                "command": "python3 real_judge.py --live",
            }))
            return
    else:
        import anthropic
        client = anthropic.Anthropic()  # uses env
        recs = []
        for i, t in enumerate(sample):
            rec = call_one(client, t)
            recs.append(rec)
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(sample)}")
            time.sleep(0.05)

    # Score
    tp = fp = tn = fn = unclear = 0
    rows = []
    tin = tout = 0
    for r in recs:
        v = parse_verdict(r["text"])
        gold_pass = bool(r["planted_process_ok"])
        tin += r["usage"]["in"]
        tout += r["usage"]["out"]
        rows.append({"trace_id": r["trace_id"], "verdict": v, "gold_pass": gold_pass,
                     "kind": r["fixture_kind"]})
        if v == "unclear":
            unclear += 1
            continue
        pred_pass = v == "pass"
        if gold_pass and pred_pass:
            tp += 1
        elif gold_pass and not pred_pass:
            fn += 1
        elif (not gold_pass) and pred_pass:
            fp += 1
        else:
            tn += 1
    P = tp + fn
    N = tn + fp
    summary = {
        "model": MODEL,
        "n": len(recs),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn, "unclear": unclear,
        "tpr": tp / P if P else None,
        "tnr": tn / N if N else None,
        "tokens_in": tin, "tokens_out": tout,
        "cost_usd_assumed": tin * PRICE_IN + tout * PRICE_OUT,
        "rows": rows,
    }
    (OUT / "judge.json").write_text(json.dumps(summary, indent=2))
    print(f"TPR {tp}/{P}  TNR {tn}/{N}  unclear {unclear}")
    print(f"tokens in {tin} out {tout} cost ~${summary['cost_usd_assumed']:.4f}")
    print("wrote out/judge.json")


if __name__ == "__main__":
    live = "--live" in sys.argv
    main(live=live)
