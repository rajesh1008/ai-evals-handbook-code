from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.inctoeval import time_to_eval_days, complaint_neighbours, taxonomy_change_from_review

OUT = Path(__file__).parent / "out"


def main():
    out = {
        "try_tte": time_to_eval_days("2029-04-24", "2029-04-28"),
        "try_neighbours": complaint_neighbours("t-390101", n=3, stratum="fee")["n"],
        "try_taxonomy": taxonomy_change_from_review("rev-x", new_failure_mode="FM-x", action="add")["produces_fix"],
    }
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
