from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.liveexp import (
    assign_unit, sequential_peeks, refine_guardrail, interleave_rankings, experiment_record,
)

OUT = Path(__file__).parent / "out"

def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    salt = "harbor-hardship-ab-2028-11"
    # assign first 200 units for illustration
    assigns = {u: assign_unit(u, salt) for u in fix["units"][:200]}
    n_c = sum(1 for v in assigns.values() if v == "control")
    n_t = sum(1 for v in assigns.values() if v == "treatment")
    looks_at = [50, 100, 200, 400]
    alpha_spend = [0.001, 0.005, 0.01, 0.04]
    peeks = sequential_peeks(fix["control_errors"], fix["treatment_errors"], alpha_spend, looks_at)
    # Pre-holiday cumulative at n=100
    pre = refine_guardrail(sum(fix["treatment_errors"][:100]), 100, target=fix["target"])
    # Holiday weekend spike on treatment arm: plant extra errors in a window (SIMULATED injection applied in inject.py)
    # Lab baseline without injection:
    mid = refine_guardrail(sum(fix["treatment_errors"][:200]), 200, target=fix["target"])
    inter = interleave_rankings(fix["control_rank"], fix["treatment_rank"], fix["clicks"])
    rec = experiment_record(
        experiment_id="exp-hardship-prompt-2028-11",
        unit="borrower",
        salt=salt,
        arms={"control": "prompt-hardship-2028-10-a", "treatment": "prompt-hardship-2028-11-b"},
        guardrail_metric=fix["guardrail_metric"],
        primary_metric=fix["primary_metric"],
        status="running",
    )
    out = {
        "kind": "SIMULATED",
        "digest": fix["digest"],
        "seed": fix["seed"],
        "assignment": {"n_control": n_c, "n_treatment": n_t, "salt": salt, "unit": "borrower"},
        "peeks": peeks,
        "guardrail_pre_holiday": pre,
        "guardrail_n200": mid,
        "interleave": inter,
        "experiment": rec,
        "study_window": fix["study_window"],
        "holiday_weekend": fix["holiday_weekend"],
        "target": fix["target"],
        "k_control_400": sum(fix["control_errors"]),
        "k_treatment_400": sum(fix["treatment_errors"]),
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("digest", "assignment", "guardrail_pre_holiday", "guardrail_n200", "interleave")}, indent=2)[:1500])

if __name__ == "__main__":
    main()
