"""Three Try-it-yourself variations for Chapter 24."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.trajectory import (
    score_trajectory, aggregate_pass_hat_k, compaction_survives, transition_matrix,
)

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
TRAJS = FIX["trajectories"]
CONSTRAINT = FIX["constraint"]

print("Try It 1: raise the checklist bar — require draft_offer plan match")
# Count how many draft trajectories would lose credit if plan must match gold plan
n = 0
lost = 0
for t in TRAJS:
    if t["action"] != "draft" or t["offer_plan"] is None:
        continue
    n += 1
    checklist = [
        {"id": "elig", "tool": "check_eligibility", "required_args": ["loan_id", "reason"]},
        {"id": "offer", "tool": "draft_offer", "args": {"loan_id": t["loan_id"], "plan": t["plan"]},
         "required_args": ["loan_id", "plan"]},
    ]
    sc = score_trajectory(t["steps"], checklist=checklist)
    if not sc["exact_match"]:
        lost += 1
print(f"  draft trajs {n}; fail plan-match checklist {lost} ({lost/n:.1%})")

print("Try It 2: pass^k at k=3 instead of k=5")
trials = [t["trials"][:3] for t in FIX["passk_tasks"]]
agg3 = aggregate_pass_hat_k(trials, k=3)
agg5 = aggregate_pass_hat_k([t["trials"] for t in FIX["passk_tasks"]], k=5)
print(f"  pass^3 = {agg3['pass_hat_k']:.3f} ({agg3['n_pass_hat_k']}/{agg3['n_tasks']})")
print(f"  pass^5 = {agg5['pass_hat_k']:.3f} ({agg5['n_pass_hat_k']}/{agg5['n_tasks']})")

print("Try It 3: compaction with FM-26 alias only (no full sentence)")
surv_full = sum(1 for t in TRAJS
                if compaction_survives(CONSTRAINT, t["compacted"]).get("survives"))
surv_alias = sum(1 for t in TRAJS
                 if compaction_survives("ZZZ_NEVER", t["compacted"],
                                        aliases=["FM-26", "stated-work"]).get("survives"))
# Most compacteds don't say FM-26; measure how many stated_work traces keep any alias
sw = [t for t in TRAJS if t["stated_work"]]
sw_surv = sum(1 for t in sw
              if compaction_survives(CONSTRAINT, t["compacted"],
                                     aliases=["FM-26", "stated-work", "employment change"]).get("survives"))
print(f"  full-constraint survival {surv_full}/{len(TRAJS)}")
print(f"  stated_work traces {len(sw)}; constraint-or-alias survival {sw_surv}/{len(sw)}")

result = {
    "try1_lost_plan_match": lost, "try1_n": n,
    "try2_pass_hat_3": agg3["pass_hat_k"], "try2_pass_hat_5": agg5["pass_hat_k"],
    "try3_stated_work_n": len(sw), "try3_surv": sw_surv,
}
(OUT / "try_its.json").write_text(json.dumps(result, indent=2))
print("wrote out/try_its.json")
