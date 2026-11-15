"""Try It Yourself variations for Chapter 9.
1. Teach C-02 the loans' nicknames (v1.1) and count what it catches and what it gets wrong.
2. Add the negation rule to C-06 and run it on the fee replay set and the April fee conversations.
3. The leap-year window: compare calendar months with days <= 365 over every pair of dates in 2027-2029.
Run: python3 try_its.py"""
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
sys.path.insert(0, str(HERE.parents[0] / "ch08"))
from truss import checks as K  # noqa: E402
import april as A  # noqa: E402
import compass_checks as CC  # noqa: E402

R = {}
rows = A.build()
apr = [A.render(r) for r in rows]
print("== 1. C-02 with nicknames")
for nick in (False, True):
    S = CC.suite(nicknames=nick)
    res, _ = S.run_all(apr)
    fl = {t["trace_id"] for t in apr if res[t["trace_id"]]["C-02"].outcome == K.FAIL}
    tru = {t["trace_id"] for t in apr if "FM-22" in t["truth"]}
    applies = sum(res[t["trace_id"]]["C-02"].outcome != K.NA for t in apr)
    print(f"  nicknames={nick}: applies to {applies}; fails {len(fl)}; true {len(fl & tru)} of {len(tru)}; false {len(fl - tru)}")
    for t in sorted(fl - tru)[:3]:
        x = next(a for a in apr if a["trace_id"] == t)
        print(f"     false: {t} '{x['message']}' -> {res[t]['C-02'].evidence}")
    R[f"nick_{nick}"] = [applies, len(fl), len(fl & tru), len(tru), len(fl - tru)]
nk = Counter(l["nickname"] for t in apr for l in t["account"]["loans"])
print("  nicknames on file:", dict(nk.most_common(8)))

print("\n== 2. C-06 with the negation rule")
fee = [t for t in apr if t["flow"] == "fee_explanation"]
rep = [A.render(r, "production") for r in A.replay_rows()]
for neg in (False, True):
    S = CC.suite(negation=neg)
    for name, ts in (("April fee conversations", fee), ("fee replay set, production", rep)):
        res, _ = S.run_all(ts)
        fl = {t["trace_id"] for t in ts if res[t["trace_id"]]["C-06"].outcome == K.FAIL}
        tru = {t["trace_id"] for t in ts if "FM-06" in t["truth"]}
        print(f"  negation={neg} {name}: fails {len(fl)}, FM-06 caught {len(fl & tru)} of {len(tru)}, false {len(fl - tru)}")
        R[f"neg_{neg}_{name[:5]}"] = [len(fl), len(fl & tru), len(tru), len(fl - tru)]
probe = ["Good news: the $25.00 late fee has been waived.",
         "Your $25.00 late fee can't be waived this time.",
         "We haven't waived it yet, but the $25.00 fee has now been waived after review.",
         "Nobody said it couldn't be waived: it has been waived."]
print("  sentences the rule reads:")
for p in probe:
    print(f"    waived {bool(CC.WAIVED.search(p))!s:<5} negated {bool(CC.NEGATED.search(p))!s:<5} | {p}")

print("\n== 3. Twelve calendar months vs 365 days, every (end, asked) pair, asked in 2027-2029, gap 360-370 days")
dis = []
d = date(2027, 1, 1)
while d <= date(2029, 12, 31):
    for gap in range(360, 371):
        end = d - timedelta(days=gap)
        if K.within_months(end, d, 12) != (gap <= 365):
            dis.append((end, d, gap))
    d += timedelta(days=1)
print(f"  pairs compared {(date(2029, 12, 31) - date(2027, 1, 1)).days + 1} days x 11 gaps; disagreements {len(dis)}")
for e, a, g in dis[:6]:
    print(f"    relief ended {e}, asked {a}, {g} days: calendar {'inside' if K.within_months(e, a, 12) else 'outside'}, "
          f"tool {'inside' if g <= 365 else 'outside'}")
months = Counter(a.strftime("%Y-%m") for _, a, _ in dis)
print("  disagreements by month asked:", dict(months))
R["leap"] = {"n": len(dis), "months": dict(months), "first": [str(x) for x in dis[0]] if dis else None}
(HERE / "out").mkdir(exist_ok=True)
(HERE / "out" / "try_its.json").write_text(json.dumps(R, indent=1, default=str))
