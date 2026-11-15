"""Chapter 14, REAL model run: a pre-labeller reads the 480 hardship traces of the weeks of 2 and 9 August
2027 (fixture) under guideline ops-1.1, three samples each at the API's default sampling settings (this SDK takes no temperature argument), and returns the required
action and a confidence from 0 to 100. Compass's reply is not shown, as in the annotation screen.
Run: python3 prelabel.py run   (needs ANTHROPIC_API_KEY; never printed). Without `run`, summarises the cache."""
import concurrent.futures as cf
import json
import re
import sys
from pathlib import Path

import fixture as F
import guideline as G

HERE = Path(__file__).resolve().parent
CACHE = HERE / "out/prelabel.jsonl"
MODEL = "claude-haiku-4-5-20251001"
K = 3
SYSTEM = ("You label hardship conversations for a consumer lender's evaluation team. Apply the guideline exactly. "
          "Reply with one line of JSON only: {\"action\": \"<label>\", \"confidence\": <0-100>}.")


def prompt(t):
    return (f"GUIDELINE\n{G.text('ops-1.1')}\nLabels: {', '.join(F.LABELS)}\n\nTRACE\n{t['text']}\n\n"
            "Which first-reply action does HP-2027-04 require? JSON only.")


def frame():
    W = F.build()
    return W[0] + W[1]


def call(job):
    import anthropic
    t, k = job
    msg = anthropic.Anthropic(max_retries=6).messages.create(
        model=MODEL, max_tokens=40, system=SYSTEM,
        messages=[{"role": "user", "content": prompt(t)}])
    return {"trace_id": t["trace_id"], "sample": k, "raw": msg.content[0].text.strip(), "model": msg.model,
            "in": msg.usage.input_tokens, "out": msg.usage.output_tokens}


def parse(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        d = {}
    a = d.get("action")
    return (a if a in F.LABELS else None), d.get("confidence")


def run():
    done = set()
    if CACHE.exists():
        done = {(r["trace_id"], r["sample"]) for r in map(json.loads, CACHE.open())}
    jobs = [(t, k) for t in frame() for k in range(K) if (t["trace_id"], k) not in done]
    print(f"calls to make: {len(jobs)}")
    with CACHE.open("a") as fh, cf.ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(call, jobs)):
            fh.write(json.dumps(r) + "\n")
            if i % 200 == 0:
                fh.flush(); print(" ", i, flush=True)


def load():
    by = {}
    for r in map(json.loads, CACHE.open()):
        a, c = parse(r["raw"])
        by.setdefault(r["trace_id"], []).append((r["sample"], a, c))
    return {t: [x[1:] for x in sorted(v)] for t, v in by.items()}


def summary():
    rows = [json.loads(l) for l in CACHE.open()]
    P = load()
    fr = {t["trace_id"]: t for t in frame()}
    unparsed = sum(a is None for v in P.values() for a, _ in v)
    print(f"REAL run, model {rows[0]['model']}: {len(rows)} calls on {len(P)} traces; tokens in {sum(r['in'] for r in rows):,}, "
          f"out {sum(r['out'] for r in rows):,}; unparsed answers {unparsed}")
    from collections import Counter
    maj = {t: Counter(a for a, _ in v).most_common(1)[0][0] for t, v in P.items()}
    right = sum(maj[t] == fr[t]["required"] for t in P)
    print(f"majority label right {right}/{len(P)} ({right / len(P):.1%})")
    return P


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        run()
    summary()
