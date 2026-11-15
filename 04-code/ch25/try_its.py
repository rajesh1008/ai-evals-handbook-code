"""Three Try-it-yourself variations."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.simuser import aggregate_conversations, fidelity_table

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
LAB = json.loads((OUT / "lab.json").read_text())
convs = FIX["conversations"]
real = FIX["real_transcripts"]

# 1. Drop polite_deferrer from the sim pool — gap should shrink
filtered = [c for c in convs if c["persona"] != "polite_deferrer"]
a1 = aggregate_conversations(filtered)
gap1 = a1["goal_completion"] - LAB["real"]["goal_completion"]

# 2. Require pushback_rate >= 0.1 for a sim conversation to count as valid eval fuel
valid = [c for c in convs if c["pushback_rate"] >= 0.1]
a2 = aggregate_conversations(valid) if valid else {"goal_completion": None, "n": 0}

# 3. Session-length strata: short (<=5 turns) vs long
short = aggregate_conversations([c for c in convs if c["n_turns"] <= 5])
long = aggregate_conversations([c for c in convs if c["n_turns"] > 5])

out = {
    "try1_drop_polite": {"n": a1["n"], "goal_completion": a1["goal_completion"], "gap_vs_real": gap1},
    "try2_min_pushback": {"n": a2["n"], "goal_completion": a2.get("goal_completion")},
    "try3_length_strata": {"short": short, "long": long},
}
(OUT / "try_its.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
