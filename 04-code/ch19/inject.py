"""Failure injection: the hardship bulletin lands and the judge is not updated.

This is the Chapter 19 injection. It reconstructs week 4 from the fixture
and contrasts it with the same fresh traces scored as if the judge had
been updated the morning the bulletin took effect (a counterfactual the
fixture plants by swapping week-4 fresh gold/pred disagreements back to
agreements for the plan_fee slice).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import weeks
from truss.drift import alert, slice_disagreements, track_split, week_report


def head(s):
    print("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)


def pct(x):
    return "nan" if x != x else f"{100 * x:.1f}%"


WS = weeks()
history = []
for w in WS:
    if w["week"] in ("w1", "w2", "w3"):
        history.append(track_split(w["rows"]))

w4 = next(w for w in WS if w["week"] == "w4")
actual = track_split(w4["rows"])
a = alert(history, actual)

head("Injection: HB-2027-12 effective Monday 6 December 2027, judge still v1")
print(f"  pooled kappa {actual['pooled']['kappa']:.4f} (rounded {actual['pooled']['kappa']:.2f})")
print(f"  alert {a['verdict']}  diagnostic {a['diagnostic']}")
print(f"  drop vs rolling median {a['drop']:.4f}  (fail at {0.15})")
print(f"  frozen kappa {actual['frozen']['kappa']:.4f}  fresh kappa {actual['fresh']['kappa']:.4f}")
print(f"  track gap {actual['gap']:.4f}")
s = slice_disagreements([r for r in w4["rows"] if r["track"] == "fresh"])
print(f"  fresh plan_fee disagreements {s['plan_fee']['disagree']}/{s['plan_fee']['n']}")
print(f"  fresh other disagreements {s['other']['disagree']}/{s['other']['n']}")

# Counterfactual: update the judge on Monday morning. The plan_fee
# disagreements become agreements; other traces are unchanged.
fixed_rows = []
for r in w4["rows"]:
    q = dict(r)
    if q["track"] == "fresh" and q["slice"] == "plan_fee" and q["truth"] != q["pred"]:
        q["pred"] = q["truth"]
    # Frozen gold is still the old policy, so a new judge would start
    # disagreeing on the eight plan_fee frozen traces. We mark that
    # separately rather than inventing a new matrix: the lesson is that
    # the frozen canary must be re-derived before it can watch v2.
    fixed_rows.append(q)

# Only rewrite fresh; leave frozen as the old-gold / old-judge pair so
# the counterfactual is "we updated the judge AND we knew not to trust
# the unrederived frozen set". Report fresh-only for the would-have-been.
fresh_fixed = [r for r in fixed_rows if r["track"] == "fresh"]
cf = week_report([r["truth"] for r in fresh_fixed], [r["pred"] for r in fresh_fixed])
head("Counterfactual: same week, judge updated on Monday morning (fresh track)")
print(f"  fresh kappa {cf['kappa']:.4f}  agree {cf['agree_n']}/{cf['n']}")
print(f"  confusion tp={cf['tp']} fn={cf['fn']} fp={cf['fp']} tn={cf['tn']}")
print("  frozen canary would need re-derivation before watching v2 "
      "(old gold vs new rule is a planned disagreement, not a fault)")

out = {
    "actual_pooled_kappa": actual["pooled"]["kappa"],
    "actual_verdict": a["verdict"],
    "actual_diagnostic": a["diagnostic"],
    "fresh_slices": s,
    "counterfactual_fresh": cf,
}
(HERE / "out").mkdir(exist_ok=True)
(HERE / "out" / "inject.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
print("\nwrote out/inject.json")
