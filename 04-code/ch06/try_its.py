"""Chapter 6 Try It Yourself: three variations on the lab."""
import contextlib
import io
import math
import random
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss import sampling as S
from truss import taxonomy as T
import january as J
import modes as M
with contextlib.redirect_stdout(io.StringIO()):
    import lab as LAB

print("== 1. re-code sample size")
for n in (100, 200, 400, 800):
    samp = S.risk_weighted(LAB.early, n, LAB.risk, seed=J.SEED)
    rows = [LAB.byid[t] for t, _ in samp]
    L = LAB.label(rows, LAB.t011)
    c = T.coverage(L)
    f2 = [l["note"] for l in L if l["code"] == "FM-02"]
    nones = [l["note"] for l in L if l["code"] is None]
    print(f"n={n:>3} drawn {len(rows):>3}: failing {c['failing']:>2}, FM-13 labels failing test "
          f"{sum(1 for l in L if l['code'] == 'FM-13' and not l['fit']):>2}, FM-02 clusters {len(T.clusters(f2))}, "
          f"'none fits' {len(nones)}, fitted {c['fitted_share']:.0%} ({c['fitted_ci'][0]:.0%} to {c['fitted_ci'][1]:.0%})")

print("\n== 2. keep FM-09 and FM-10 apart instead of merging")
rng = random.Random(J.SEED + 7)
pay = [r for r in LAB.frame if r["cause"] in ("P_perdiem", "P_goodthru")][:200]
a = [J.first_coder(r, "0.1.1") for r in pay]
b = [J.second_coder(r, "0.1.1", rng) for r in pay]
print(f"{len(pay)} payoff failures from the frame, two coders, v0.1.1 codes: agreement {sum(x == y for x, y in zip(a, b)) / len(pay):.0%}, "
      f"kappa {T.kappa(a, b):.2f}")
print(f"merged into FM-19: agreement 100%, kappa undefined (one code); facet kept in a field, not a code")
for conf in (.1, .2, .3):
    rng = random.Random(J.SEED)
    b2 = [x if rng.random() >= conf else {"FM-09": "FM-10", "FM-10": "FM-09"}[x] for x in a]
    print(f"   if coders confused them {conf:.0%} of the time: kappa {T.kappa(a, b2):.2f}")

print("\n== 3. retirement bound")
for bound in (.05, .02, .01):
    n = T.clean_traces_to_retire(bound)
    print(f"upper bound {bound:.0%}: {n} clean fee traces; at 20 a week of monitoring, {math.ceil(n / 20)} weeks")
print(f"zero in 20 bounds the rate at {T.zero_bound(20):.1%}; zero in {LAB.R['retire']['fee_read_since_removal']} at {T.zero_bound(LAB.R['retire']['fee_read_since_removal']):.1%}")
