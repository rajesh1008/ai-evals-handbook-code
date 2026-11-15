"""Try It Yourself, three variations. 1 and 2 SIMULATED readers; 3 is a REAL model run (21 to 85 calls).
Run: python3 try_its.py [1|2|3]"""
import concurrent.futures as cf
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

import fixture as F
import lab
import prelabel as P
from truss import annotation as AN

HERE = Path(__file__).resolve().parent


def one():
    """No triple reads in week 1: does the anniversary gap still surface before the Friday session?"""
    from truss import annotation
    orig = annotation.assign
    for tri in (0.2, 0.0):
        annotation.assign = lambda ids, readers, triple=0.2, **kw: orig(ids, readers, triple=tri if len(readers) == 3 else triple, **kw)
        lab.AN.assign = annotation.assign
        weeks = lab.run()
        wk = weeks[0]
        surfaced = [t for t in wk["anniv"] if len(set(wk["readings"][t].values())) > 1]
        wrong = [t for t in wk["anniv"] if wk["final"][t] != wk["required"][t]]
        print(f"  triple share {tri}: week-one anniversary traces {len(wk['anniv'])}, surfaced as a disagreement {len(surfaced)}, "
              f"final label wrong {len(wrong)}; week-one reads {wk['reads']}")
    annotation.assign = lab.AN.assign = orig


def two():
    """Mixed selection with 15 or 30 targeted reads out of 60 (REAL pre-labels)."""
    import random
    pre = P.load()
    W = F.build(); frame = {t["trace_id"]: t for t in W[0] + W[1]}; ids = sorted(frame)
    fail = {t: int(frame[t]["required"] != "cannot_tell" and frame[t]["compass"] != frame[t]["required"]) for t in ids}
    maj = {t: Counter(a for a, _ in pre[t]).most_common(1)[0][0] for t in ids}
    flagged = [t for t in ids if maj[t] != frame[t]["compass"]]
    for k in (0, 15, 30, 45):
        rows = []
        for s in range(1000):
            if k == 0:
                pick, inc = AN.select(ids, 60, "random", seed=s)
            else:
                pick, inc = AN.select(ids, 60, "mixed", seed=s, mix_targeted=k, pool=flagged)
            rows.append((sum(fail[t] for t in pick), AN.ht_rate(fail, inc, len(ids))))
        print(f"  targeted {k:>2} of 60: failures found {st.mean(r[0] for r in rows):.1f}, "
              f"rate estimate mean {st.mean(r[1] for r in rows):.3f}, sd {st.pstdev(r[1] for r in rows):.3f} (true {sum(fail.values()) / len(ids):.3f})")


def three():
    """REAL: the pre-labeller under ops-1.0 (without the two sentences) on the anniversary and stated-work traces,
    one sample each, against sample 0 of the main run under ops-1.1."""
    import guideline as G
    cache = HERE / "out/try3_ops10.jsonl"
    frame = P.frame()
    cases = [t for t in frame if F.is_anniversary(t["facts"]) or F.is_stated_work(t["facts"])]
    done = {json.loads(l)["trace_id"] for l in cache.open()} if cache.exists() else set()
    todo = [t for t in cases if t["trace_id"] not in done]
    if todo:
        import anthropic
        def call(t):
            p = P.prompt(t).replace(G.text("ops-1.1"), G.text("ops-1.0"))
            m = anthropic.Anthropic(max_retries=6).messages.create(model=P.MODEL, max_tokens=40, system=P.SYSTEM,
                                                                   messages=[{"role": "user", "content": p}])
            return {"trace_id": t["trace_id"], "raw": m.content[0].text.strip(), "model": m.model}
        with cache.open("a") as fh, cf.ThreadPoolExecutor(8) as ex:
            for r in ex.map(call, todo):
                fh.write(json.dumps(r) + "\n")
    got = {r["trace_id"]: P.parse(r["raw"])[0] for r in map(json.loads, cache.open())}
    main = P.load()
    for name, fn in [("anniversary", F.is_anniversary), ("stated work", F.is_stated_work)]:
        xs = [t for t in cases if fn(t["facts"])]
        a = sum(got[t["trace_id"]] == t["required"] for t in xs)
        b = sum(main[t["trace_id"]][0][0] == t["required"] for t in xs)
        print(f"  REAL {P.MODEL}, {name} traces (n {len(xs)}): right under ops-1.0 {a}, under ops-1.1 {b} (sample 0 of the main run)")


if __name__ == "__main__":
    which = sys.argv[1:] or ["1", "2", "3"]
    for w in which:
        print(f"== Try it {w}"); {"1": one, "2": two, "3": three}[w]()
