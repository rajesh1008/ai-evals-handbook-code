from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.inctoeval import (
    time_to_eval_days,
    incident_record,
    regression_case,
    symptom_vs_failure_mode,
    replay_on_releases,
    complaint_neighbours,
    weekly_report,
    taxonomy_change_from_review,
)

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    ttes = []
    cases = []
    replays = []
    neighbour_total = 0
    for inc in fix["incidents"]:
        tte = time_to_eval_days(inc["opened"], inc["eval_merged"])
        ttes.append(tte)
        rec = incident_record(
            inc["incident_id"],
            opened=inc["opened"],
            symptom=inc["symptom"],
            failure_mode=inc["failure_mode"],
            owner=inc["owner"],
        )
        nb = complaint_neighbours(inc["seed_trace"], n=fix["neighbours_per_incident"], stratum=inc["stratum"])
        neighbour_total += nb["n"]
        case = regression_case(
            f"case-{inc['incident_id']}",
            incident_id=inc["incident_id"],
            failure_mode=inc["failure_mode"],
            against="failure_mode",
            owner=inc["owner"],
            neighbour_ids=nb["neighbour_ids"],
        )
        cases.append(case)
        replays.append(replay_on_releases(case, fix["releases"]))
        _ = rec
    median_tte = sorted(ttes)[len(ttes) // 2]
    report = weekly_report(
        median_tte_days=float(median_tte),
        n_incidents_closed_to_eval=len(cases),
        n_symptom_rejected=1,
        complaints_this_month=fix["complaints_this_month"],
        complaints_prev_month=fix["complaints_prev_month"],
    )
    tax = taxonomy_change_from_review("rev-3901", new_failure_mode="FM-fee-sycophancy", action="add")
    # sidebar: one complaint → neighbours + seed ≈ 41 if 3*13+2
    sidebar_n = neighbour_total + 2
    out = {
        "seed": fix["seed"],
        "digest": fix["digest"],
        "simulated": True,
        "ttes": ttes,
        "median_tte_days": median_tte,
        "tte_before_days": fix["tte_before_days"],
        "tte_improved": median_tte <= fix["tte_after_median"],
        "cases": cases,
        "replays": replays,
        "neighbour_total": neighbour_total,
        "sidebar_cases": sidebar_n,
        "weekly": report,
        "taxonomy_change": tax,
        "teaching": {
            "three_incidents_to_cases": len(cases) == 3,
            "tte_19_to_4": fix["tte_before_days"] == 19 and median_tte == 4,
            "complaints_falling": report["complaints_falling"],
            "all_fm_cases": all(c["against"] == "failure_mode" for c in cases),
        },
        "study_window": fix["study_window"],
        "scoreboard_date": fix["scoreboard_date"],
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("digest", "median_tte_days", "teaching", "weekly", "sidebar_cases")}, indent=2))


if __name__ == "__main__":
    main()
