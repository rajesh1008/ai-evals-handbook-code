"""Chapter 13 Try It Yourself (SIMULATED officers, as in lab.py).
  1. Skip the agreed-label audit: how many gold labels are wrong?
  2. One reader plus a 20% second read instead of two readers on everything.
  3. Let sittings run to 90 minutes instead of 45.
Run after lab.py: python3 try_its.py"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss import adjudication as J  # noqa: E402
import fixture as F  # noqa: E402
import officers as O  # noqa: E402

T = F.build(); by = {t["trace_id"]: t for t in T}
recs = json.load(open(HERE / "out" / "records.json"))
labs = [J.Label(**x) for x in json.load(open(HERE / "out" / "labels.json"))]

print("== 1. Without the agreed-label audit")
audited = [r for r in recs if r["audit"]]
wrong_without = sum(1 for r in audited if r["labels"][0][1] != by[r["trace_id"]]["final_action"])
print(f"  agreed labels the audit reopened: {len(audited)}; kept as agreed, {wrong_without} would be wrong against the final policy, "
      f"and every one of the {sum(r['kind'] == 'policy' for r in audited)} policy cases would carry a label nobody had ruled on")

print("== 2. One reader on everything, a second reader on a 20% sample")
final = {}
for x in labs:
    final[(x.trace_id, x.annotator)] = x  # the last label each reader gave a trace
g = random.Random(7)
ids = sorted({t for t, _ in final})
second = set(g.sample(ids, len(ids) // 5))
gold = {r["trace_id"]: r["gold"] for r in recs if r["status"] == "final"}
single_wrong = sum(1 for t in ids if t in gold and final[(t, "grace")].label != gold[t] and t not in second)
caught = sum(1 for t in second if t in gold and final[(t, "grace")].label != gold[t])
mins = lambda who, sel: sum(final[(t, who)].minutes for t in sel) / 60
print(f"  traces {len(ids)}; second-read sample {len(second)}; single-read labels that differ from the adjudicated gold "
      f"and were never second-read: {single_wrong}; differences the sample found: {caught}")
print(f"  reading hours: double {mins('grace', ids) + mins('ben', ids):.1f}; single plus 20% {mins('grace', ids) + mins('ben', second):.1f}")
print(f"  what the sample estimates: disagreement rate {caught}/{len(second)} = {caught / len(second):.1%}, "
      f"so about {round(caught / len(second) * (len(ids) - len(second)))} wrong labels left in the unread 80%")

print("== 3. Sittings of up to 90 minutes")
for cap in (45, 90):
    g = random.Random(F.SEED + 13); slips = n = 0
    order = T[:]; random.Random(F.SEED).shuffle(order)
    for name in ("grace", "ben"):
        minute = 0.0
        for t in order[40:160]:
            m = O.minutes_for(name, t, g)
            if minute + m > cap:
                minute = 0.0
            minute += m
            lab, _, _ = O.read(name, t, "r3", "2027-07-06", minute, g)
            slips += lab != O.intended(name, t, "r3", "2027-07-06"); n += 1
    print(f"  cap {cap} minutes: {slips} slipped labels in {n} ({slips / n:.1%})")
