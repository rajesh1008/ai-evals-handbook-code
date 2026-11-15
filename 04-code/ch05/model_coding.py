"""Model-assisted coding, run for real against Anthropic models (needs ANTHROPIC_API_KEY).
Two experiments on the 53 pooled failing notes from lab.py:
  1. open grouping: the model groups the notes by shared cause with no codebook;
  2. closed coding: the model assigns each note one taxonomy v0.1 code, or NONE.
Both are scored against the codes the axial session assigned. Raw responses are cached in
out/model/ so the numbers reproduce without a key; pass --live to call the API again.
The Compass traces in this fixture carry placeholder message text, so the model reads the
notes people wrote, not the conversations."""
import json
import os
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.coding import cohen_kappa, confusion, purity  # noqa: E402
import codebook as K  # noqa: E402

OUT = Path(__file__).parent / "out" / "model"
OUT.mkdir(parents=True, exist_ok=True)
MODELS = ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"]
LIVE = "--live" in sys.argv

pool = json.load(open(Path(__file__).parent / "out" / "lab.json"))["pool"]
ids = [f"n{i:02d}" for i in range(1, len(pool) + 1)]
human = {i: p[4] for i, p in zip(ids, pool)}
lines = "\n".join(f"{i} [{p[2]}] {p[3]}" for i, p in zip(ids, pool))


def call(model, prompt, tag):
    path = OUT / f"{tag}--{model}.json"
    if path.exists() and not LIVE:
        return json.load(open(path))
    body = json.dumps({"model": model, "max_tokens": 4000, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
        "content-type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=180))
    rec = {"model": model, "text": r["content"][0]["text"], "usage": r["usage"]}
    json.dump(rec, open(path, "w"), indent=1)
    return rec


def parse(text):
    s, e = text.find("{"), text.rfind("}")
    return json.loads(text[s:e + 1])


OPEN = f"""You are helping with error analysis of a loan-servicing chat assistant called Compass.
Below are {len(pool)} notes, one per failing conversation, written by human reviewers. Each line
has an id, the conversation's flow in brackets, and the note.

Group the notes into failure categories so that notes in one category share a cause and would
share a fix. Use as many or as few categories as the notes need. Every note goes in exactly one
category. Reply with JSON only, in this shape:
{{"groups": [{{"name": "short name", "why": "one sentence", "ids": ["n01", "n02"]}}]}}

{lines}
"""

defs = "\n".join(f"{c} {n}: {d}" for c, n, _, d, *_ in K.V01)
CLOSED = f"""You are coding failing conversations from a loan-servicing chat assistant called Compass
against a failure taxonomy. Assign each note exactly one code from the list, or NONE if no
definition fits.

{defs}

Notes (id, [flow], note):
{lines}

Reply with JSON only: {{"codes": {{"n01": "FM-05", ...}}}}
"""

print(f"notes {len(pool)}; human categories {len(set(human.values()))}")
cost = Counter()
for m in MODELS:
    rec = call(m, OPEN, "open")
    cost[m] += rec["usage"]["input_tokens"] + rec["usage"]["output_tokens"]
    groups = parse(rec["text"])["groups"]
    g_ids = [g["ids"] for g in groups]
    placed = [i for g in g_ids for i in g]
    pur = purity([[i for i in g if i in human] for g in g_ids if any(i in human for i in g)], human)
    # completeness: share of notes whose human category sits mostly in one model group
    where = defaultdict(Counter)
    for k, g in enumerate(g_ids):
        for i in g:
            if i in human:
                where[human[i]][k] += 1
    comp = sum(c.most_common(1)[0][1] for c in where.values()) / len(human)
    split = sorted(code for code, c in where.items() if len(c) > 1)
    merged = sorted({tuple(sorted({human[i] for i in g if i in human})) for g in g_ids
                     if len({human[i] for i in g if i in human}) > 1})
    print(f"\n1. open grouping, {m}")
    print(f"   groups {len(groups)}; notes placed {len(placed)} of {len(pool)} (duplicates {len(placed) - len(set(placed))})")
    print(f"   purity {pur:.0%}; completeness {comp:.0%}")
    print(f"   human categories split across model groups: {split}")
    print(f"   model groups mixing human categories: {merged}")
    for g in groups:
        print(f"     {len(g['ids']):2}  {g['name']}  -> {dict(Counter(human.get(i, '?') for i in g['ids']))}")

for m in MODELS:
    rec = call(m, CLOSED, "closed")
    cost[m] += rec["usage"]["input_tokens"] + rec["usage"]["output_tokens"]
    codes = parse(rec["text"])["codes"]
    mine = [human[i] for i in ids]
    theirs = [codes.get(i, "MISSING") for i in ids]
    agree = sum(a == b for a, b in zip(mine, theirs))
    print(f"\n2. closed coding against v0.1, {m}")
    print(f"   agreement {agree}/{len(ids)}; kappa {cohen_kappa(mine, theirs):.3f}")
    for (a, b), n in sorted(confusion(mine, theirs).items()):
        ex = [pool[k][3] for k, i in enumerate(ids) if human[i] == a and codes.get(i) == b][0]
        print(f"     human {a} -> model {b} x{n}: \"{ex}\"")
print(f"\ntokens used: {dict(cost)}")
