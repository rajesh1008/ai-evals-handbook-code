from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.reviewer import override_rate, automation_bias_rate, per_reviewer_table

OUT = Path(__file__).parent / "out"

def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    rows = fix["rows"]
    # 1: drop rubber-stamper
    without = [r for r in rows if r["reviewer_id"] != "R-ryan"]
    # 2: hide AI advice on wrong plants
    blind = []
    for r in rows:
        rr = dict(r)
        if rr["ai_wrong"]:
            rr["saw_ai"] = False
            # when blind, human recovers toward gold more often (SIMULATED)
            if rr["human_label"] != rr["gold"] and rr["ai_label"] != rr["gold"]:
                rr["human_label"] = rr["gold"]
                rr["final_label"] = rr["gold"]
        blind.append(rr)
    # 3: second review on disagreements only
    disag = [r for r in rows if r["human_label"] != r["gold"]]
    out = {
        "try1_without_rubber": {"n": len(without), "override_rate": override_rate(without)["override_rate"]},
        "try2_blind_on_plants": {
            "bias_with_ai": automation_bias_rate(rows),
            "bias_blind_simulated": automation_bias_rate(blind),
        },
        "try3_disagreement_pool": {"n": len(disag), "per_reviewer_errors": {
            r["reviewer_id"]: sum(1 for x in disag if x["reviewer_id"] == r["reviewer_id"])
            for r in per_reviewer_table(rows)
        }},
        "simulated": True,
    }
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
