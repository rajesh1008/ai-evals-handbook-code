"""Chapter 7 Try It Yourself: three variations on the February notebook."""
import contextlib
import io
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss import notebook as NBK
from truss import sampling as S
import february as FEB
with contextlib.redirect_stdout(io.StringIO()):
    import lab as L

good = [r for r in L.frame if r["status"] != "abandoned"]
read = set(L.ids)
pool = [r for r in good if r["trace_id"] not in read]      # what a fresh fifty can draw from
by = L.by
WANT = {"FM-22": lambda r: r["cause"] == "X_wrongloan", "FM-23": lambda r: r["cause"] == "L_address",
        "FM-24": lambda r: r["cause"] == "X_invent",
        "wrong offer": lambda r: r["offered_loan_recent_deferral"]}


def sweep(drawer, seeds=200):
    hits, hard, fails = Counter(), 0, []
    for s in range(1, seeds + 1):
        rows = [by[t] for t in drawer(s)]
        hard += sum(r["flow"] == "hardship" for r in rows)
        fails.append(sum(1 for r in rows if r["cause"]))
        for k, f in WANT.items():
            hits[k] += any(f(r) for r in rows)
    sweep.fails = (sum(fails) / seeds, sum(f >= 10 for f in fails) / seeds)
    return {k: hits[k] / seeds for k in WANT}, hard / seeds


print("\n== Try it 1: 25, 50 or 100 traces (same quotas, scaled; 200 seeds; the read fifty excluded)")
for scale in (0.5, 1, 2):
    q = {f: max(1, round(n * scale)) for f, n in FEB.QUOTAS.items()}
    p, h = sweep(lambda s: [t for t, _, _ in NBK.pps_quota(pool, "flow", q, L.risk, seed=s)])
    print(f"  n={sum(q.values()):>3}: " + ", ".join(f"{k} {v:.0%}" for k, v in p.items()) + f"; hardship read {h:.0f}; failures per draw {sweep.fails[0]:.1f}, ten or more {sweep.fails[1]:.0%}")

print("\n== Try it 2: a uniform fifty instead of risk-weighted quotas")
p, h = sweep(lambda s: [t for t, _ in S.uniform(pool, 50, seed=s)])
print("  uniform: " + ", ".join(f"{k} {v:.0%}" for k, v in p.items()) + f"; hardship read {h:.1f}; failures per draw {sweep.fails[0]:.1f}")

print("\n== Try it 3: second reading of the first reader's failures only (the Chapter 6 shortcut)")
own_fail = {e.n for e in L.first if e.verdict == "fail"}
kept = [a for a in L.adj if a["n"] in own_fail]
lost = [a for a in L.adj if a["n"] not in own_fail]
print(f"  first reader's failures {len(own_fail)}; second readings needed {len(own_fail)} instead of 50")
print(f"  disagreements still found {len(kept)}: {[a['n'] for a in kept]}; never seen {len(lost)}: "
      + ", ".join(f"{a['n']} (final {a['final']})" for a in lost))
mins = sum(10 if 26 <= n <= 40 else 3 for n in own_fail)
print(f"  second-reading minutes {mins} instead of {15 * 10 + 35 * 3}; a real failure missed: "
      f"{[a['n'] for a in lost if a['final'] != 'pass']}")
