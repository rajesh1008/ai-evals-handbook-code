"""SIMULATED Harbor incident→eval panel for Chapter 39."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"
SEED = 2039

INCIDENTS = [
    {
        "incident_id": "inc-3901",
        "opened": "2029-04-24",
        "symptom": "Borrower praised; fee amount wrong",
        "failure_mode": "FM-fee-sycophancy",
        "owner": "eval-lead",
        "eval_merged": "2029-04-28",
        "seed_trace": "t-390101",
        "stratum": "fee",
    },
    {
        "incident_id": "inc-3902",
        "opened": "2029-04-26",
        "symptom": "Hardship SMS silent wrong eligibility",
        "failure_mode": "FM-hardship-silent-fail",
        "owner": "compass-eng",
        "eval_merged": "2029-04-30",
        "seed_trace": "t-390201",
        "stratum": "hardship",
    },
    {
        "incident_id": "inc-3903",
        "opened": "2029-05-01",
        "symptom": "Tool said confirmed after killed process",
        "failure_mode": "FM-compaction-fabricate",
        "owner": "platform",
        "eval_merged": "2029-05-05",
        "seed_trace": "t-390301",
        "stratum": "tools",
    },
]

RELEASES = [
    {"name": "r-2029-03", "fails_modes": ["FM-fee-sycophancy", "FM-hardship-silent-fail", "FM-compaction-fabricate"], "symptom_still_visible": True},
    {"name": "r-2029-03b", "fails_modes": ["FM-fee-sycophancy", "FM-hardship-silent-fail", "FM-compaction-fabricate"], "symptom_still_visible": True},
    {"name": "r-2029-04", "fails_modes": ["FM-fee-sycophancy", "FM-hardship-silent-fail"], "symptom_still_visible": False},
    {"name": "r-2029-04b", "fails_modes": ["FM-hardship-silent-fail"], "symptom_still_visible": False},
    {"name": "r-2029-05", "fails_modes": [], "symptom_still_visible": False},
]


def build():
    payload = json.dumps({"seed": SEED, "incidents": [i["incident_id"] for i in INCIDENTS]}, sort_keys=True)
    dig = hashlib.sha256(payload.encode()).hexdigest()[:12]
    return {
        "seed": SEED,
        "simulated": True,
        "label": "SIMULATED",
        "digest": dig,
        "incidents": INCIDENTS,
        "releases": RELEASES,
        "tte_before_days": 19,
        "tte_after_median": 4,
        "complaints_prev_month": 42,
        "complaints_this_month": 31,
        "study_window": "Mon 23 Apr 2029 – Mon 21 May 2029",
        "scoreboard_date": "Mon 21 May 2029",
        "neighbours_per_incident": 13,  # 1+13=14; the sidebar case uses forty-one (13*3+2=41)
    }


def main():
    OUT.mkdir(exist_ok=True)
    fix = build()
    (OUT / "fixture.json").write_text(json.dumps(fix, indent=2))
    print(fix["digest"], len(fix["incidents"]))


if __name__ == "__main__":
    main()
