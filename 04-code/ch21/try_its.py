"""Chapter 21 Try It Yourself. SIMULATED verdicts (fixture.py, seed 2026); Truss computes the numbers."""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "truss"))
from truss.trial import validation_table
from truss.bias import pairwise_agree, majority
import fixture as fx

dev, test = fx.build()
out = {}
print("=" * 100)
print("Try It 1: run the trial on the 120 random production offers only")
print("=" * 100)
rnd = [r for r in test if r["source"] == "random"]
t1 = validation_table([r["gold"] for r in rnd], [r["v1"] for r in rnd], [r["kind"] for r in rnd])
print(f"  gold wrong offers {t1['P']}; TPR {t1['tp']}/{t1['P']} ({t1['tpr_ci'][0]:.3f} to {t1['tpr_ci'][1]:.3f}); "
      f"TNR {t1['tn']}/{t1['N']} = {t1['tnr']:.3f} ({t1['tnr_ci'][0]:.3f} to {t1['tnr_ci'][1]:.3f}); "
      f"agreement {t1['agree_n']}/{t1['n']} = {100 * t1['agreement']:.1f}%; kappa {t1['kappa']:.3f}")
out["random_only"] = t1

print()
print("=" * 100)
print("Try It 2: give hardship-judge-v1 the C-03 v1.1 window result as an input, no new rules")
print("=" * 100)
t2 = validation_table([r["gold"] for r in test], [r["v1_c03"] for r in test], [r["kind"] for r in test])
print(f"  TPR {t2['tp']}/{t2['P']} = {t2['tpr']:.3f} ({t2['tpr_ci'][0]:.3f} to {t2['tpr_ci'][1]:.3f}); "
      f"TNR {t2['tn']}/{t2['N']} = {t2['tnr']:.3f} ({t2['tnr_ci'][0]:.3f} to {t2['tnr_ci'][1]:.3f}); kappa {t2['kappa']:.3f}")
for k in ("window", "anniversary_outside", "stated_work", "stated_correct"):
    print(f"    {k:20s} right {t2['by_kind'][k]['right']}/{t2['by_kind'][k]['n']}  (v1 without the input: "
          f"{sum(1 for r in test if r['kind'] == k and r['v1'] == r['gold'])})")
out["c03_input"] = t2

print()
print("=" * 100)
print("Try It 3: a panel of three (v1 and two paraphrased prompts), majority vote")
print("=" * 100)
# Paraphrase panels are SIMULATED: each copies v1 and re-decides a seeded tenth of v1's agreements
# and a third of its disagreements, so the three share most mistakes (same model, same reading).
rng = random.Random(fx.SEED + 3)
panel = [[r["v1"] for r in test]]
for _ in range(2):
    p = []
    for r in test:
        v = r["v1"]
        if v == r["gold"] and rng.random() < 0.06:
            v = "pass" if v == "fail" else "fail"
        elif v != r["gold"] and rng.random() < 0.34:
            v = r["gold"]
        p.append(v)
    panel.append(p)
maj = majority(panel, tie="cannot_tell")
t3 = validation_table([r["gold"] for r in test], maj, [r["kind"] for r in test])
pa = [pairwise_agree(panel[i], panel[j]) for i, j in ((0, 1), (0, 2), (1, 2))]
pa = [x["rate"] if isinstance(x, dict) else x for x in pa]
print(f"  panel pairwise agreement {', '.join(f'{x:.3f}' for x in pa)}; each member against gold "
      + ", ".join(f"{sum(1 for v, r in zip(p, test) if v == r['gold'])}/200" for p in panel))
print(f"  majority: TPR {t3['tp']}/{t3['P']} = {t3['tpr']:.3f} ({t3['tpr_ci'][0]:.3f} to {t3['tpr_ci'][1]:.3f}); "
      f"TNR {t3['tn']}/{t3['N']} = {t3['tnr']:.3f} ({t3['tnr_ci'][0]:.3f} to {t3['tnr_ci'][1]:.3f}); "
      f"agreement {t3['agree_n']}/200; kappa {t3['kappa']:.3f}")
out["panel"] = {"pairwise": pa, "majority": t3}
json.dump(out, open(HERE / "out" / "try_its.json", "w"), indent=1, default=str)
