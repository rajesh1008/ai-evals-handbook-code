"""Chapter 13: can a model find the ambiguous guideline sentence before two officers spend six hours
finding it in the kappa? REAL model calls (claude-haiku-4-5-20251001 and claude-sonnet-4-6), three
runs each on revision 2 and revision 3, cached to out/probe.jsonl. The key is read by the SDK from the
environment and never printed.
Usage: python3 probe.py run, then python3 probe.py"""
import concurrent.futures as cf
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "ch12")); sys.path.insert(0, str(HERE.parents[0] / "truss"))
from policy import POLICY_TEXT  # noqa: E402
from truss.fields import parse_json  # noqa: E402
from guideline import REVISIONS  # noqa: E402
sys.path.insert(0, str(HERE.parents[0]))
import llm_backend as LB  # noqa: E402

LOCAL = LB.is_local()
MODELS = {"local": LB.model()} if LOCAL else {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-4-6"}
RAW = LB.pick(HERE, HERE / "out" / "probe.jsonl", "probe-local.jsonl")
PROMPT = """Two experienced loan officers will label the same hardship conversations independently, using the labelling guideline below, and their labels will be compared. Find the guideline sentences that two careful officers could apply differently to the same conversation.

The policy the guideline implements:
{policy}

The guideline:
{guideline}

For each sentence ID, decide whether two careful officers who both follow it could still give different labels to some conversation. Only count a real difference in the label, not wording or style. Return one JSON object: {{"sentences": [{{"id": "G-01", "ambiguous": true or false, "readings": ["...", "..."], "example": "a conversation where the readings give different labels, or null"}}, ...]}}. No other text."""


def call(job):
    m, rev, rep = job
    g = "\n".join(f"{k} {v}" for k, v in REVISIONS[rev].items())
    if LOCAL:
        r = LB.chat(PROMPT.format(policy=POLICY_TEXT, guideline=g), max_tokens=4000)
        return {"model": MODELS[m], "revision": rev, "rep": rep, "raw": r["text"], "in_tok": r["in_tok"],
                "out_tok": r["out_tok"], "label": LB.LABEL}
    import anthropic
    msg = anthropic.Anthropic().messages.create(model=MODELS[m], max_tokens=4000, messages=[
        {"role": "user", "content": PROMPT.format(policy=POLICY_TEXT, guideline=g)}])
    return {"model": MODELS[m], "revision": rev, "rep": rep, "raw": msg.content[0].text,
            "in_tok": msg.usage.input_tokens, "out_tok": msg.usage.output_tokens}


def cached():
    return [json.loads(x) for x in RAW.read_text().splitlines()] if RAW.exists() else []


if __name__ == "__main__":
    if LOCAL:
        LB.require_local(); LB.banner("guideline ambiguity probe")
    if LB.live_requested(sys.argv) or LOCAL:
        done = {(c["model"], c["revision"], c["rep"]) for c in cached()}
        jobs = [(m, r, k) for m in MODELS for r in ("r2", "r3") for k in range(3) if (MODELS[m], r, k) not in done]
        with cf.ThreadPoolExecutor(4) as ex, RAW.open("a") as fh:
            for r in ex.map(call, jobs):
                fh.write(json.dumps(r) + "\n"); fh.flush()
    if not cached():
        LB.skip("probe.py (guideline ambiguity probe)", "out/probe.jsonl", "./run_all.sh run")
        sys.exit(0)
    out = {}
    for c in sorted(cached(), key=lambda c: (c["model"], c["revision"], c["rep"])):
        obj, _ = parse_json(c["raw"])
        flags = [s["id"] for s in (obj or {}).get("sentences", []) if s.get("ambiguous")]
        g06 = next((s for s in (obj or {}).get("sentences", []) if s.get("id") == "G-06"), {})
        key = f"{c['model']} {c['revision']}"
        out.setdefault(key, []).append({"flags": flags, "g06": g06})
        print(f"{key} run {c['rep']}: flagged {flags}")
        if g06.get("ambiguous"):
            print(f"    G-06 readings: {g06.get('readings')}")
    print("\nsummary (runs flagging each sentence, of 3):")
    for key, runs in out.items():
        cnt = Counter(f for r in runs for f in r["flags"])
        print(f"  {key}: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    json.dump(out, open(LB.pick(HERE, HERE / "out" / "probe.json"), "w"), indent=1)
