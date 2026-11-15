"""Try-it witnesses for Ch46 validation pack."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def main():
    lab = json.loads((OUT / "lab.json").read_text())
    inj = json.loads((OUT / "inject.json").read_text())
    try_its = {
        "try_rebuild_table": {
            "instruction": "Recompute hardship_overall_pre_post from fixture k/n; match table_sha12",
            "expected_sha12": lab["table_sha12"],
        },
        "try_catch_metric_drift": {
            "instruction": "Diff pack_metric vs dashboard_metric_drift; require caught=true",
            "expected_caught": True,
            "actual_caught": inj["caught"],
        },
        "anti_patterns": [
            "Treat public benchmark score as Harbor validation",
            "Claim SR 26-2 covers generative Compass as in-scope model",
            "Author alone signs MEETS without challenger",
            "Ship while pack/dashboard metric unit disagrees",
        ],
    }
    (OUT / "try_its.json").write_text(json.dumps(try_its, indent=2) + "\n")
    print("try_its ok")


if __name__ == "__main__":
    main()
