"""Chapter 19 lab: two-track monitoring, the policy-change drop, versioning.

Prints every number the chapter uses and writes out/lab.json. No model is
called. Judges and gold are SIMULATED (see fixture.py). Truss computations
are real.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import (
    FROZEN_CHECKS, MODEL_PIN, NEW_RUBRIC, OLD_RUBRIC, PROMPT_V1, SEED,
    describe, revalidation_rows, weeks,
)
from truss.drift import (
    THRESHOLDS, alert, change_control, revalidate, slice_disagreements,
    track_split, version_record, week_report,
)

OUT: dict = {"seed": SEED, "thresholds": dict(THRESHOLDS)}


def head(s):
    print("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)


def pct(x):
    return "nan" if x != x else f"{100 * x:.1f}%"


def show_report(label, r):
    print(f"  {label}: n={r['n']}  agree {r['agree_n']}/{r['n']} = {pct(r['agreement'])}  "
          f"kappa {r['kappa']:.4f} (rounded {r['kappa']:.2f})  "
          f"TPR {r['tp']}/{r['P']} = {pct(r['tpr'])} "
          f"(Wilson {pct(r['tpr_ci'][0])} to {pct(r['tpr_ci'][1])})  "
          f"TNR {r['tn']}/{r['N']} = {pct(r['tnr'])} "
          f"(Wilson {pct(r['tnr_ci'][0])} to {pct(r['tnr_ci'][1])})")
    print(f"           confusion tp={r['tp']} fn={r['fn']} fp={r['fp']} tn={r['tn']}")


def jsonable(obj):
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, float) and obj != obj:
        return None
    return obj


head("1. Fixture (SIMULATED): six weekly canaries of 100, seed 2026")
d = describe()
print(f"frozen {d['frozen_ids'][0]} to {d['frozen_ids'][1]} ({d['n_frozen']})")
print(f"fresh {d['n_fresh']} a week; weeks {', '.join(d['weeks'])}")
print(f"policy change {d['policy_change']} effective {d['effective']}")
print(f"fixture digest {d['fixture_digest']}")
OUT["fixture"] = d

WS = weeks()
reports = []
head("2. Weekly two-track reports")
for w in WS:
    split = track_split(w["rows"])
    rec = {
        "week": w["week"], "start": w["start"], "policy": w["policy"],
        "judge": w["judge"], **split,
    }
    reports.append(rec)
    print(f"\n{w['week']} starting {w['start']}  policy {w['policy']}  judge {w['judge']}")
    show_report("frozen", split["frozen"])
    show_report("fresh ", split["fresh"])
    show_report("pooled", split["pooled"])
    print(f"  track gap (frozen minus fresh) {split['gap']:.4f}")

OUT["weeks"] = [
    {
        "week": r["week"], "start": r["start"], "policy": r["policy"],
        "judge": r["judge"],
        "frozen": r["frozen"], "fresh": r["fresh"], "pooled": r["pooled"],
        "gap": r["gap"],
    }
    for r in reports
]

head("3. Alerts against the rolling median of prior weeks")
alerts = []
for i, rec in enumerate(reports):
    history = [{"frozen": r["frozen"], "fresh": r["fresh"], "pooled": r["pooled"],
                "gap": r["gap"]} for r in reports[:i]]
    this = {"frozen": rec["frozen"], "fresh": rec["fresh"], "pooled": rec["pooled"],
            "gap": rec["gap"]}
    a = alert(history, this)
    alerts.append({"week": rec["week"], **a})
    print(f"  {rec['week']}: verdict {a['verdict']:4s}  diagnostic {a['diagnostic']:12s}  "
          f"kappa {a['kappa']:.4f}  baseline {a['baseline'] if a['baseline']==a['baseline'] else float('nan'):}  "
          f"drop {a['drop'] if a['drop']==a['drop'] else float('nan')}  "
          f"frozen_drop {a['frozen_drop'] if a['frozen_drop']==a['frozen_drop'] else float('nan')}  "
          f"fresh_drop {a['fresh_drop'] if a['fresh_drop']==a['fresh_drop'] else float('nan')}  "
          f"gap {a['gap']:.4f}")

OUT["alerts"] = alerts

head("4. Week-4 disagreements by slice (fresh track only)")
w4 = next(w for w in WS if w["week"] == "w4")
fresh4 = [r for r in w4["rows"] if r["track"] == "fresh"]
sliced = slice_disagreements(fresh4)
for name, rec in sliced.items():
    print(f"  {name}: n={rec['n']}  disagree {rec['disagree']}/{rec['n']} "
          f"= {pct(rec['disagree_rate'])}  agree {rec['agree']}")
OUT["w4_fresh_slices"] = sliced
pooled_slices = slice_disagreements(w4["rows"])
OUT["w4_pooled_slices"] = pooled_slices
print("  pooled (frozen+fresh):")
for name, rec in pooled_slices.items():
    print(f"    {name}: n={rec['n']}  disagree {rec['disagree']}/{rec['n']} "
          f"= {pct(rec['disagree_rate'])}")

head("5. Judge versions (content-addressed)")
v1 = version_record(
    "fee-judge-v1", PROMPT_V1, MODEL_PIN, OLD_RUBRIC,
    "HP-2027-04", "MC-02 v1.1", "decide", admitted_on="2027-11-15")
v2 = version_record(
    "fee-judge-v2", PROMPT_V1, MODEL_PIN, NEW_RUBRIC,
    "HB-2027-12", "MC-02 v1.1", "decide", admitted_on="2027-12-17")
v1_again = version_record(
    "fee-judge-v1", PROMPT_V1, MODEL_PIN, OLD_RUBRIC,
    "HP-2027-04", "MC-02 v1.1", "decide", admitted_on="2027-12-01")
print(f"  fee-judge-v1 digest {v1['digest']}  admitted {v1['admitted_on']}")
print(f"  fee-judge-v2 digest {v2['digest']}  admitted {v2['admitted_on']}")
print(f"  same content, later date, same digest: {v1['digest'] == v1_again['digest']}")
print(f"  v1 and v2 differ: {v1['digest'] != v2['digest']}")
OUT["versions"] = {"v1": v1["digest"], "v2": v2["digest"],
                   "same_content_same_digest": v1["digest"] == v1_again["digest"]}

head("6. Change-control gate on the rubric")
silent = change_control(OLD_RUBRIC, NEW_RUBRIC, frozen_ids=FROZEN_CHECKS)
print(f"  unapproved rewrite of waive_or_charge: {silent['verdict']}  "
      f"unapproved {silent['rewritten_unapproved']}")
ruled = change_control(
    OLD_RUBRIC, NEW_RUBRIC, frozen_ids=FROZEN_CHECKS,
    allowed_rewrites={"waive_or_charge": "HB-2027-12"})
print(f"  rewrite citing HB-2027-12: {ruled['verdict']}  "
      f"approved {ruled['rewritten_approved']}  rulings {ruled['rulings']}")
deleted = [c for c in NEW_RUBRIC if c["id"] != "window"]
held = change_control(
    OLD_RUBRIC, deleted, frozen_ids=FROZEN_CHECKS,
    allowed_rewrites={"waive_or_charge": "HB-2027-12"})
print(f"  same rewrite plus a deleted window check: {held['verdict']}  "
      f"deleted_frozen {held['deleted_frozen']}")
OUT["change_control"] = {
    "silent": silent, "ruled": ruled, "deleted_window": held,
}

head("7. Re-validation of fee-judge-v2 on 200 freshly labelled traces")
rv_rows = revalidation_rows()
rv = week_report([r["truth"] for r in rv_rows], [r["pred"] for r in rv_rows])
decision = revalidate(rv)
show_report("revalidation", rv)
print(f"  admit? {decision['verdict']}  reasons {decision['reasons'] or 'none'}")
print(f"  TPR Wilson lower bound {decision['tpr_lo']:.4f} (floor 0.80)")
print(f"  TNR Wilson lower bound {decision['tnr_lo']:.4f} (floor 0.90)")
print(f"  kappa {decision['kappa']:.4f} (floor 0.75)")
OUT["revalidation"] = {"report": rv, "decision": decision}

# A 100-trace peek at the same quality as a healthy week cannot clear the floors.
peek = reports[0]["pooled"]
peek_decision = revalidate(peek)
print(f"  week-1 pooled n=100 as a 'revalidation': {peek_decision['verdict']}  "
      f"reasons {peek_decision['reasons']}")
OUT["peek_w1"] = {"report": peek, "decision": peek_decision}

head("8. Cost sketch (illustrative rates stated as such)")
# Ch14 cost per final label $13.90; frozen traces are re-judged, not relabelled.
label_cost = 13.90
weekly_fresh = 60 * label_cost
weekly_frozen_calls = 40 * 0.00143
reval_labels = 200 * label_cost
frozen_rederive = 40 * label_cost
print(f"  weekly fresh labels 60 x ${label_cost:.2f} = ${weekly_fresh:.2f}")
print(f"  weekly frozen re-judge 40 x $0.00143 = ${weekly_frozen_calls:.4f}")
print(f"  one-off revalidation 200 x ${label_cost:.2f} = ${reval_labels:.2f}")
print(f"  one-off frozen re-derivation 40 x ${label_cost:.2f} = ${frozen_rederive:.2f}")
print(f"  recovery package (revalidation + re-derive) = ${reval_labels + frozen_rederive:.2f}")
OUT["cost"] = {
    "label_cost": label_cost,
    "weekly_fresh": weekly_fresh,
    "weekly_frozen_calls": weekly_frozen_calls,
    "revalidation": reval_labels,
    "frozen_rederive": frozen_rederive,
    "recovery_package": reval_labels + frozen_rederive,
}

out_dir = HERE / "out"
out_dir.mkdir(exist_ok=True)
payload = jsonable(OUT)
(out_dir / "lab.json").write_text(json.dumps(payload, indent=2) + "\n")
print("\nwrote out/lab.json")
