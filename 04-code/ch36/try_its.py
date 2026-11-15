from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.liveexp import assign_unit, interleave_rankings, refine_guardrail

OUT = Path(__file__).parent / "out"

def main():
    a1 = assign_unit("b-900001", "harbor-hardship-ab-2028-11")
    a2 = assign_unit("b-900001", "different-salt")
    inter = interleave_rankings(
        ["a", "b", "c"],
        ["b", "a", "d"],
        ["b"],
    )
    g = refine_guardrail(3, 40, target=0.005)
    out = {
        "same_unit_stable_arm": a1,
        "salt_change_may_flip": a2,
        "interleave_winner": inter["winner"],
        "small_n_guardrail_trip": g["trip"],
    }
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2))
    print(out)

if __name__ == "__main__":
    main()
