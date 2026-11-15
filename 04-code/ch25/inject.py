"""Failure injection: swap in a never-push-back persona; hides wrong-offer fails."""
from __future__ import annotations
import json, copy, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.simuser import aggregate_conversations, polite_mask_failure

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
convs = copy.deepcopy(FIX["conversations"])

# Plant: 20 conversations where Compass drafts a wrong hardship offer,
# but the polite simulator never challenges → outcome still "resolved".
planted = []
for c in convs:
    if c["persona"] == "polite_deferrer" and c["goal_completed"] and len(planted) < 20:
        c["wrong_offer_hidden"] = True
        c["process_ok"] = False  # trajectory would fail; outcome passes
        planted.append(c["trace_id"])

agg = aggregate_conversations(convs)
# outcome-only looks fine
outcome_ok = agg["goal_completion"]
# process-aware: subtract hidden wrong offers
process_ok_n = sum(1 for c in convs if c["goal_completed"] and not c.get("wrong_offer_hidden"))
process_rate = process_ok_n / len(convs)

polite = [c for c in convs if c["persona"] == "polite_deferrer"]
mean_pb = sum(c["pushback_rate"] for c in polite) / len(polite)

result = {
    "n_planted_hidden_wrong": len(planted),
    "planted_ids": planted[:5],
    "named": planted[0] if planted else None,
    "outcome_goal_completion": outcome_ok,
    "process_aware_completion": process_rate,
    "gap_hidden": outcome_ok - process_rate,
    "polite_mean_pushback": mean_pb,
    "polite_masks": polite_mask_failure(mean_pb),
    "lesson": "A simulator that never pushes back scores outcome success on wrong offers.",
}
(OUT / "inject.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
