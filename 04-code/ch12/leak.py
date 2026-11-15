"""Chapter 12, real model run and failure injection: golden cases leaked into Compass's knowledge base.

Eighty admitted synthetic cases (16 per policy action, seed 2026) are the test set; their labels come
from policy.decide. A small fast model decides the first-reply action with the policy text and two
'worked examples' retrieved from the knowledge base. Clean run: the two examples are other synthetic
cases. Leaked run: for 40 of the 80 (8 per action), one example is the test case itself with its answer,
which is what happens when someone pastes eval cases into the knowledge base as examples.

Usage: python3 leak.py run   (calls the API; caches out/leak.jsonl)
       python3 leak.py       (scores the cache, runs the leak scan, writes out/leak.json)
"""
import json, random, re, sys, concurrent.futures as cf
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.datasets import leak_scan
from truss.rates import wilson
from policy import POLICY_TEXT, ACTIONS

HERE = Path(__file__).resolve().parent
CACHE = HERE / "out/leak.jsonl"
MODEL = "claude-haiku-4-5-20251001"
CANARY = "HL-GOLDEN-7f3a"   # carried in every golden case file header since v1.0


def facts(c):
    r = c["raw"]
    loans = "; ".join(f"{l['product']} loan ending {l['last4']}, {l['payments_behind']} payments behind" for l in r["loans"])
    pr = r["prior_relief"]
    prior = f"{pr['type']} ended {pr['months_ago']} calendar months ago" if pr else "none on record"
    return f"Account records: {loans}. Employment on file: {r['income_type']}. Prior relief: {prior}."


def example(c):
    return f"Borrower: {c['raw']['message']}\n{facts(c)}\nCorrect first-reply action: {c['policy_label']}"


def design(seed=2026):
    cases = [c for c in json.load(open(HERE / "out/synth_cases.json")) if c.get("admitted")]
    g = random.Random(seed)
    test, leaked = [], set()
    for a in ACTIONS:
        xs = [c for c in cases if c["policy_label"] == a]
        pick = g.sample(xs, 16)
        test += pick
        leaked |= {c["sid"] for c in pick[:8]}
    tids = {c["sid"] for c in test}
    pool = [c for c in cases if c["sid"] not in tids]
    jobs = []
    for c in test:
        ex = g.sample(pool, 2)
        jobs.append({"sid": c["sid"], "cond": "clean", "leaked": c["sid"] in leaked, "examples": [e["sid"] for e in ex]})
        exl = ([c, ex[1]] if c["sid"] in leaked else ex)
        jobs.append({"sid": c["sid"], "cond": "leaked_index", "leaked": c["sid"] in leaked, "examples": [e["sid"] for e in exl]})
    return cases, test, pool, jobs


def prompt(c, exs):
    kb = "\n\n".join(example(e) for e in exs)
    return (f"You are Compass, Harbor Lending's servicing assistant.\n\n{POLICY_TEXT}\n\n"
            f"Worked examples retrieved from the knowledge base:\n\n{kb}\n\n"
            f"New conversation.\nBorrower: {c['raw']['message']}\n{facts(c)}\n\n"
            f"Answer with exactly one action name from: {', '.join(ACTIONS)}.")


def call(job, by):
    import anthropic
    c, exs = by[job["sid"]], [by[s] for s in job["examples"]]
    msg = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=20,
                                               messages=[{"role": "user", "content": prompt(c, exs)}])
    return dict(job, answer=msg.content[0].text.strip(), model=msg.model)


def load():
    return [json.loads(l) for l in open(CACHE)] if CACHE.exists() else []


def score():
    cases, test, pool, jobs = design()
    by = {c["sid"]: c for c in cases}
    rows = load()
    out = {}
    for cond in ("clean", "leaked_index"):
        for lk in (True, False):
            xs = [r for r in rows if r["cond"] == cond and r["leaked"] == lk]
            k = sum(next((a for a in ACTIONS if a in r["answer"]), None) == by[r["sid"]]["policy_label"] for r in xs)
            lo, hi = wilson(k, len(xs))
            out[f"{cond}/{'leaked' if lk else 'not_leaked'}"] = {"k": k, "n": len(xs), "acc": k / len(xs) if xs else None, "lo": lo, "hi": hi}
    # the scan: knowledge-base documents against the golden case texts
    kb = {f"kb-policy-{i}": line for i, line in enumerate(POLICY_TEXT.split("\n"))}
    for s in sorted({r["sid"] for r in rows if r["leaked"]}):
        kb[f"kb-example-{s}"] = f"{CANARY} " + example(by[s])
    for c in pool[:60]:
        kb[f"kb-example-{c['sid']}"] = example(c)      # 60 legitimate worked examples, not in the test set
    hits = leak_scan(kb, [{"case_id": c["sid"], "text": c["raw"]["message"]} for c in test], n=8, threshold=0.3, canaries=(CANARY,))
    out["scan"] = {"docs": len(kb), "hits": len(hits), "leaked_docs_found": len({h[0] for h in hits}),
                   "legit_docs_flagged": len({h[0] for h in hits if not h[3]}), "canary_hits": sum(h[3] for h in hits),
                   "min_containment_true": min(h[2] for h in hits if h[0].endswith(h[1]))}
    clean = [r for r in rows if r["cond"] == "clean"]
    out["clean_by_action"] = {a: [sum(next((x for x in ACTIONS if x in r["answer"]), None) == a for r in clean if by[r["sid"]]["policy_label"] == a), 16] for a in ACTIONS}
    flips = [(r["sid"]) for r in rows if r["cond"] == "leaked_index" and r["leaked"]]
    out["leaked_fixed"] = sum(1 for s in flips if next(a for a in ACTIONS if a in [x for x in rows if x["sid"] == s and x["cond"] == "leaked_index"][0]["answer"] or True) and
                              (next((a for a in ACTIONS if a in [x for x in rows if x["sid"] == s and x["cond"] == "clean"][0]["answer"]), None) != by[s]["policy_label"]) and
                              (next((a for a in ACTIONS if a in [x for x in rows if x["sid"] == s and x["cond"] == "leaked_index"][0]["answer"]), None) == by[s]["policy_label"]))
    out["calls"] = len(rows)
    out["model"] = rows[0]["model"] if rows else None
    json.dump(out, open(HERE / "out/leak.json", "w"), indent=1)
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        cases, test, pool, jobs = design()
        by = {c["sid"]: c for c in cases}
        done = {(r["sid"], r["cond"]) for r in load()}
        todo = [j for j in jobs if (j["sid"], j["cond"]) not in done]
        with cf.ThreadPoolExecutor(8) as ex, open(CACHE, "a") as f:
            for r in ex.map(lambda j: call(j, by), todo):
                f.write(json.dumps(r) + "\n"); f.flush()
    print(json.dumps(score(), indent=1))
