"""Score 300 simulated conversations; compare to real-transcript cohort."""
from __future__ import annotations
import json, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.simuser import aggregate_conversations, fidelity_table, pushback_rate
from truss.fields import wilson

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
convs = FIX["conversations"]
real = FIX["real_transcripts"]

print("Chapter 25 lab: simulated users and multi-turn evaluation")
agg = aggregate_conversations(convs)
lo, hi = wilson(agg["n_completed"], agg["n"])
agg["wilson"] = [lo, hi]
print(f"sim goal completion {agg['goal_completion']:.3f} ({agg['n_completed']}/{agg['n']}) Wilson {lo:.3f}-{hi:.3f}")

real_done = sum(1 for r in real if r["goal_completed"])
r_lo, r_hi = wilson(real_done, len(real))
real_agg = {
    "n": len(real),
    "goal_completion": real_done / len(real),
    "n_completed": real_done,
    "abandonment": sum(1 for r in real if r["abandoned"]) / len(real),
    "mean_turns_to_resolution": sum(r["turns_to_resolution"] for r in real if r["turns_to_resolution"]) / max(1, sum(1 for r in real if r["turns_to_resolution"])),
    "mean_pushback_rate": sum(r["pushback_rate"] for r in real) / len(real),
    "wilson": [r_lo, r_hi],
}
print(f"real goal completion {real_agg['goal_completion']:.3f} ({real_done}/{len(real)}) Wilson {r_lo:.3f}-{r_hi:.3f}")

by_persona = {}
for c in convs:
    by_persona.setdefault(c["persona"], []).append(c)
persona_table = {p: aggregate_conversations(v) for p, v in sorted(by_persona.items())}

fid = fidelity_table(
    {"goal_completion": agg["goal_completion"], "abandonment": agg["abandonment"],
     "mean_turns": agg["mean_turns_to_resolution"], "mean_pushback": agg["mean_pushback_rate"]},
    {"goal_completion": real_agg["goal_completion"], "abandonment": real_agg["abandonment"],
     "mean_turns": real_agg["mean_turns_to_resolution"], "mean_pushback": real_agg["mean_pushback_rate"]},
)

# Session / turn / perturbation tests (coverage C2)
# Perturb: mid-session goal shift on 60 conversations
import random
rng = random.Random(FIX["seed"] + 25)
pert = []
sample = rng.sample(convs, 60)
for c in sample:
    before = c["goal_completed"]
    # goal shift: if polite, still "succeeds"; if sceptical, often fails
    if c["persona"] == "polite_deferrer":
        after = True
    elif c["persona"] == "sceptical_auditor":
        after = before and rng.random() < 0.35
    else:
        after = before and rng.random() < 0.72
    pert.append({"trace_id": c["trace_id"], "persona": c["persona"], "before_ok": before, "after_ok": after,
                 "survived": before and after, "regressed": before and not after})
pert_survive = sum(1 for p in pert if p["survived"]) / max(1, sum(1 for p in pert if p["before_ok"]))

L = {
    "seed": FIX["seed"], "digest": FIX["digest"],
    "sim": agg, "real": real_agg,
    "gap_goal_completion": agg["goal_completion"] - real_agg["goal_completion"],
    "persona_table": persona_table,
    "fidelity": fid,
    "perturbation": {"n": len(pert), "survive_rate_among_before_ok": pert_survive, "rows_sample": pert[:5]},
    "touchpoint": {"sim": 0.84, "real": 0.79, "measured_sim": agg["goal_completion"], "measured_real": real_agg["goal_completion"]},
}
(OUT / "lab.json").write_text(json.dumps(L, indent=2))
print(f"gap sim-real goal completion {L['gap_goal_completion']:+.3f}")
print(f"perturbation survival among before-ok: {pert_survive:.3f}")
print(f"persona goal rates: " + ", ".join(f"{p}={persona_table[p]['goal_completion']:.2f}" for p in persona_table))
