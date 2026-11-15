"""Chapter 21 failure injection: split hardship-judge-v1 into two narrower judges. One still fails.
SIMULATED verdicts (fixture.py, seed 2026); Truss 0.24 `trial` computes every number."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "truss"))
from truss.trial import validation_table, admit_part, split_verdict, construct_profile, decision_record
import fixture as fx

dev, test = fx.build()
print("=" * 100)
print("Failure injection: the split. Part A reads, part B decides; code results go to part B as inputs")
print("=" * 100)
ja = validation_table([r["ja_gold"] for r in test], [r["ja"] for r in test], [r["kind"] for r in test])
jb = validation_table([r["gold"] for r in test], [r["jb"] for r in test], [r["kind"] for r in test])
for name, t in (("stated-change-judge-v1 (A)", ja), ("permission-judge-v1 (B)", jb)):
    print(f"{name:28s} TPR {t['tp']}/{t['P']} = {t['tpr']:.3f} ({t['tpr_ci'][0]:.3f} to {t['tpr_ci'][1]:.3f})  "
          f"TNR {t['tn']}/{t['N']} = {t['tnr']:.3f} ({t['tnr_ci'][0]:.3f} to {t['tnr_ci'][1]:.3f})  kappa {t['kappa']:.3f}")
pa = admit_part("stated-change-judge-v1", ja, role="order")
pb = admit_part("permission-judge-v1", jb, role="decide")
for p in (pa, pb):
    print(f"  admit {p['part']}: {p['admit']}  role {p['role']}  reasons {p['reasons']}")
sv = split_verdict([pa, pb], gate_needs=["stated-change-judge-v1", "permission-judge-v1"])
print(f"split serves the MC-01 gate: {sv['gate_allowed']}  failed parts {sv['failed_parts']}  admitted {sv['admitted']}")
print()
print("Where part B still misses (gold wrong offers it passed), by kind:")
miss = {}
for r in test:
    if r["gold"] == "fail" and r["jb"] != "fail":
        miss[r["kind"]] = miss.get(r["kind"], 0) + 1
for k, v in sorted(miss.items(), key=lambda kv: -kv[1]):
    print(f"  {k:12s} {v}")
reading = miss.get("stated_work", 0) + miss.get("income", 0)
print(f"  misses on what the borrower said (stated_work + income): {reading}/{sum(miss.values())}")
base, pres, types, ch_v1, ch_jb = fx.construct_edits()
cpb = construct_profile(base, pres, ch_jb, types)
print(f"part B sensitivity on the same 40 minimal edits: R = {cpb['R_k']}/{cpb['R_n']} = {cpb['R']:.3f}  "
      + "  ".join(f"{t} {v['changed']}/{v['n']}" for t, v in cpb["R_by_type"].items()))
print()
print("Decision record, Friday 21 January 2028 (evidence as it stood that morning)")
dr = decision_record({
    "fix": {"held_out_clean": False, "admitted": False, "weeks": 10, "cost": 2780},
    "split": {"held_out_clean": False, "admitted": False, "weeks": 10, "cost": 2780},
    "abandon": {"replacement": ["C-02 loan", "C-03 v1.1 window", "C-09 referral on record",
                                "weekly gold labels for MC-01 and MC-17", "officer approval of every draft",
                                "stated-change-judge-v1 orders targeted reading"], "weeks": 0, "cost": 0},
})
for k, v in dr.items():
    print(f"  {k:8s} supported today {v['supported_today']!s:5s}  why not {v['why_not']}  "
          f"clean evidence in about {v['weeks']} weeks, about ${v['cost']:,}")
json.dump({"ja": ja, "jb": jb, "admit_a": pa, "admit_b": pb, "split": sv, "jb_miss": miss,
           "construct_jb": cpb, "decision": dr}, open(HERE / "out" / "inject.json", "w"), indent=1, default=str)
