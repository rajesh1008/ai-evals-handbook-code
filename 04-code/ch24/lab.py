"""Chapter 24 lab: score hardship trajectories. Reads fixture; writes out/lab.json."""
from __future__ import annotations
import json, sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.trajectory import (
    score_trajectory, detect_loops, recovery, lucky_pass, transition_matrix,
    aggregate_pass_hat_k, pass_hat_k_unbiased, compaction_survives, step_efficiency,
)
from truss.fields import wilson

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
TRAJS = FIX["trajectories"]
TASKS = FIX["passk_tasks"]
CONSTRAINT = FIX["constraint"]
L = {"seed": FIX["seed"], "n": FIX["n"], "digest": FIX["digest"]}

print("Chapter 24 lab: evaluating agent trajectories")
print(f"n={FIX['n']} digest={FIX['digest']} kinds={FIX['kind_counts']}")

# 1. Step efficiency and loops
# Touchpoint metric: kind=="loop" (re-entered get_loan after failed eligibility) = 23%.
# detect_loops also flags recovery retries and abandon clarification repeats.
kind_looped = sum(1 for t in TRAJS if t["kind"] == "loop")
detect_looped = 0
eff_rows = []
for t in TRAJS:
    d = detect_loops(t["steps"])
    if d["looped"]:
        detect_looped += 1
    ref_len = 5 if t["action"] in ("draft", "refer") else None
    eff_rows.append(step_efficiency(t["steps"], reference_len=ref_len))
loop_share = kind_looped / len(TRAJS)
L["loops"] = {"n_looped": kind_looped, "share": loop_share,
              "detect_loops_n": detect_looped,
              "detect_loops_share": detect_looped / len(TRAJS),
              "target_touchpoint": 0.23,
              "mean_steps": sum(e["n_steps"] for e in eff_rows) / len(eff_rows)}
print(f"\n1. Loops (kind): {kind_looped}/{len(TRAJS)} = {loop_share:.1%} (touchpoint 23%); "
      f"detect_loops any-repeat: {detect_looped}/{len(TRAJS)}")

# 2. Lucky-pass audit
lp = []
for t in TRAJS:
    checklist = [
        {"id": "loan", "tool": "get_loan", "required_args": ["loan_id"]},
        {"id": "borrower", "tool": "get_borrower", "required_args": ["borrower_id"]},
        {"id": "policy", "tool": "lookup_policy", "required_args": ["topic"]},
        {"id": "elig", "tool": "check_eligibility", "required_args": ["loan_id", "reason"]},
    ]
    sc = score_trajectory(t["steps"], checklist=checklist)
    row = lucky_pass(t["outcome_ok"], t["process_ok"])
    row["trace_id"] = t["trace_id"]
    row["fixture_kind"] = t["kind"]
    row["partial"] = sc["partial"]
    lp.append(row)
audit_counts = Counter(r["kind"] for r in lp)
fixture_kinds = Counter(r["fixture_kind"] for r in lp)
lucky_n = audit_counts["lucky_pass"]
L["lucky"] = {"counts": dict(audit_counts), "fixture_kinds": dict(fixture_kinds),
              "n_lucky_pass": lucky_n,
              "share_of_outcome_ok": lucky_n / max(1, audit_counts["lucky_pass"] + audit_counts["true_success"]),
              "named": "t-270087",
              "named_detail": next(r for r in lp if r["trace_id"] == "t-270087")}
print(f"2. Lucky-pass audit: {dict(audit_counts)}")
print(f"   named t-270087 -> {L['lucky']['named_detail']['kind']} (fixture {L['lucky']['named_detail']['fixture_kind']})")

# 3. Partial credit vs binary
partials = [r["partial"] for r in lp]
binary_success = sum(1 for t in TRAJS if t["outcome_ok"]) / len(TRAJS)
mean_partial = sum(partials) / len(partials)
L["partial"] = {"mean_partial": mean_partial, "binary_outcome_ok": binary_success,
                "gap": binary_success - mean_partial}
print(f"3. Partial credit mean {mean_partial:.3f} vs binary outcome {binary_success:.3f}")

# 4. Transition-failure heatmap
# Tag failed steps: status error OR kind wrong_offer on draft_offer OR missing required
tagged = []
for t in TRAJS:
    steps = []
    for s in t["steps"]:
        failed = s["status"] == "error"
        # also mark compute_plan in lucky as a process failure transition
        if s["tool"] == "compute_plan" and t["kind"] == "lucky":
            failed = True
        if s["tool"] == "draft_offer" and t["kind"] == "wrong_offer":
            failed = True
        steps.append({**s, "failed": failed})
    tagged.append(steps)
tm = transition_matrix(tagged, fail_when="__never__")  # use failed flag
# top failure transitions
fail_items = sorted(((k, tm["fails"].get(k, 0), tm["counts"][k], tm["rates"][k])
                     for k in tm["counts"] if tm["fails"].get(k, 0) > 0),
                    key=lambda x: (-x[1], x[0]))
L["transitions"] = {
    "n_traj": tm["n_trajectories"],
    "top_failures": [{"from": a, "to": b, "fails": f, "n": n, "rate": r}
                     for (a, b), f, n, r in fail_items[:12]],
}
print("4. Top transition failures:")
for row in L["transitions"]["top_failures"][:8]:
    print(f"   {row['from']} -> {row['to']}: {row['fails']}/{row['n']} ({row['rate']:.0%})")

# 5. Recovery
rec_events = []
for t in TRAJS:
    r = recovery(t["steps"])
    rec_events.append(r)
n_err = sum(r["n_errors"] for r in rec_events)
n_rec = sum(r["n_recovered"] for r in rec_events)
L["recovery"] = {"n_errors": n_err, "n_recovered": n_rec,
                 "rate": (n_rec / n_err) if n_err else None}
print(f"5. Recovery: {n_rec}/{n_err} = {L['recovery']['rate']}")

# 6. pass^k
trials = [t["trials"] for t in TASKS]
agg = aggregate_pass_hat_k(trials, k=5)
# also unbiased per task then mean
unb = [pass_hat_k_unbiased(5, t["n_success"], 5) for t in TASKS]
L["passk"] = {**agg, "mean_unbiased_pass_hat_5": sum(unb) / len(unb),
              "n_tasks": len(TASKS)}
print(f"6. pass^5: {agg['n_pass_hat_k']}/{agg['n_tasks']} = {agg['pass_hat_k']:.3f}; "
      f"pass@5 = {agg['pass_at_k']:.3f}")

# 7. Compaction
surv = []
for t in TRAJS:
    c = compaction_survives(CONSTRAINT, t["compacted"], aliases=["FM-26", "stated-work check"])
    surv.append(c["survives"])
L["compaction"] = {"n": len(surv), "survived": sum(surv),
                   "rate": sum(surv) / len(surv),
                   "dropped_flag_agree": sum(1 for t, s in zip(TRAJS, surv)
                                             if (not t["compaction_dropped"]) == s) / len(TRAJS)}
print(f"7. Compaction survival: {sum(surv)}/{len(surv)} = {L['compaction']['rate']:.1%}")

# 8. Reference exact match among draftable clean-ish
exact = 0
eligible = 0
for t in TRAJS:
    if t["reference"] is None:
        continue
    eligible += 1
    sc = score_trajectory(t["steps"], reference=t["reference"])
    if sc.get("exact_match"):
        exact += 1
L["reference"] = {"eligible": eligible, "exact": exact,
                  "rate": exact / eligible if eligible else None}
print(f"8. Reference exact match: {exact}/{eligible}")

# Wilson on loop share
w = wilson(kind_looped, len(TRAJS))
L["loops"]["wilson95"] = w
print(f"   loop Wilson95: {w}")

(OUT / "lab.json").write_text(json.dumps(L, indent=2, default=str))
print(f"\nwrote {OUT / 'lab.json'}")
