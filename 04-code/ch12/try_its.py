"""Chapter 12, Try It Yourself: three variations on the lab's own data (no new model calls)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.datasets import near_duplicates, mdd
from truss.rates import upper_bound, traces_needed
from policy import ACTIONS
import leak

HERE = Path(__file__).resolve().parent
cases = json.load(open(HERE / "out/synth_cases.json"))
ok = [c for c in cases if c["schema"] and not c["consistency"]]

print("Try 1: move the near-duplicate threshold on the 381 consistent synthetic messages")
for t in (0.2, 0.3, 0.4, 0.5):
    pairs = near_duplicates([c["raw"]["message"] for c in ok], threshold=t)
    print(f"  Jaccard >= {t}: {len(pairs)} pairs, {len({j for _, j, _ in pairs})} cases dropped")

print("Try 2: score the clean leak run against the generator's labels instead of the policy's")
by = {c["sid"]: c for c in cases}
rows = [r for r in leak.load() if r["cond"] == "clean"]
ans = lambda r: next((a for a in ACTIONS if a in r["answer"]), None)
kp = sum(ans(r) == by[r["sid"]]["policy_label"] for r in rows)
kg = sum(ans(r) == by[r["sid"]]["raw"]["expected_decision"] for r in rows)
dis = sum(by[r["sid"]]["policy_label"] != by[r["sid"]]["raw"]["expected_decision"] for r in rows)
print(f"  policy labels: {kp}/{len(rows)}; generator labels: {kg}/{len(rows)}; test cases where the two labels differ: {dis}")
d = [r for r in rows if by[r["sid"]]["policy_label"] != by[r["sid"]]["raw"]["expected_decision"]]
print(f"  on those {len(d)}: the model agrees with the policy on {sum(ans(r) == by[r['sid']]['policy_label'] for r in d)}, "
      f"with the generator's wrong label on {sum(ans(r) == by[r['sid']]['raw']['expected_decision'] for r in d)}")

print("Try 3: enrich the adversarial slice instead of sampling it in proportion")
for n in (12, 59, 150, 300):
    print(f"  n={n:3d}: smallest detectable drop from 78% = {100 * mdd(n, .78):.1f} pts; zero-failure bound {100 * upper_bound(0, n):.1f}%")
for per_week in (25, 40, 60):
    print(f"  hardship at {per_week} a week from 262: {max(0, traces_needed(.005, 1) - 262) / per_week:.1f} weeks to 947 (one failure)")
adm = [c for c in cases if c.get("admitted")]
sig = lambda r: (r["income_type"], len(r["loans"]), r["language"], (r["prior_relief"] or {}).get("months_ago"),
                 r["income_monthly"] is None, max(l["payments_behind"] for l in r["loans"]))
from collections import Counter
cnt = Counter(sig(c["raw"]) for c in adm)
print(f"  (fact signatures among the {len(adm)} admitted: {len(cnt)} distinct; the commonest covers {cnt.most_common(1)[0][1]} cases)")
