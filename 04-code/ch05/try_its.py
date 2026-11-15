"""Try It Yourself: three variations on the December reading. Each repeats the draw over
200 seeds and counts what a reader who notices every planted failure would have found."""
import random
from collections import Counter

import reading as R
from truss.coding import OpenCode, saturation_curve, last_new
import codebook as K

con = R.store()
tr = R.truth()
code = {t: K.CODE_OF[R.CAUSE[m]] for t, m in tr["mode"].items() if tr["fail"].get(t)}
SEEDS = range(200)
RES = {"draw": {}, "scale": {}, "order": {}}


def found(picked):
    f = [t for t in picked if t in code]
    return len(f), len({code[t] for t in f})


def summary(rows):
    n = len(rows)
    fails = sorted(r[0] for r in rows)
    modes = sorted(r[1] for r in rows)
    return (sum(fails) / n, fails[n // 10], fails[9 * n // 10], sum(modes) / n, modes[n // 10], modes[9 * n // 10])


print("1. Uniform against risk-weighted, same quotas (mean failures [10th-90th], mean modes [10th-90th])")
for name, uni in (("uniform", True), ("risk-weighted", False)):
    rows = [found(R.draw(con, seed=s, uniform=uni)[0]) for s in SEEDS]
    m = summary(rows)
    RES["draw"][name] = m
    print(f"   {name:14} failures {m[0]:.1f} [{m[1]}-{m[2]}]  modes {m[3]:.1f} [{m[4]}-{m[5]}]")

print("2. Read more: quotas scaled (risk-weighted)")
for scale in (0.5, 1, 2, 4):
    q = {f: max(1, round(n * scale)) for f, n in R.QUOTA.items()}
    rows = [found(R.draw(con, seed=s, quota=q)[0]) for s in range(100)]
    m = summary(rows)
    all13 = sum(1 for r in rows if r[1] == 13)
    RES["scale"][sum(q.values())] = list(m) + [all13]
    print(f"   {sum(q.values()):4} traces: failures {m[0]:.1f}, modes {m[3]:.1f} [{m[4]}-{m[5]}], all thirteen in {all13} of 100")

print("3. Reading order: shuffled against flow by flow (December draw), last new category at")
picked = R.draw(con)[0]
flow = dict(con.execute("SELECT trace_id, flow FROM traces"))
for name, order in (("shuffled", None), ("flow by flow", sorted(picked, key=lambda t: (R.FLOWS.index(flow[t]), t)))):
    if order is None:
        order = picked[:]
        random.Random(R.SEED + 5).shuffle(order)
    codes = [OpenCode(i, t, "sample", flow[t], "fail" if t in code else "pass", category=code.get(t, ""))
             for i, t in enumerate(order, 1)]
    curve = saturation_curve(codes)
    RES["order"][name] = [[n, k] for n, _, k in curve]
    print(f"   {name:13} trace {last_new(curve):3}; categories at 50/100/150: "
          f"{[k for n, _, k in curve if n in (50, 100, 150)]}")

import json
from pathlib import Path
json.dump(RES, open(Path(__file__).parent / "out" / "try_its.json", "w"))
