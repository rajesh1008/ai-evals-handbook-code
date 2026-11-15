"""SIMULATED weekly series for Harbor Compass — Chapter 40.
Not real borrower history. Seed 2040. Digest content-addressed later.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"

# Eight weeks ending Mon 28 May 2029. Overall stays flat-ish; hardship rises late.
# Denominators are conversation counts in the weekly stratified monitor draw.
WEEKS = [
    # week_ending, overall_f, overall_n, hardship_f, hardship_n, fee_f, fee_n
    ("2029-04-09", 3, 900, 1, 180, 2, 200),
    ("2029-04-16", 3, 900, 1, 180, 2, 200),
    ("2029-04-23", 4, 920, 1, 185, 2, 205),
    ("2029-04-30", 3, 910, 1, 182, 1, 202),
    ("2029-05-07", 4, 930, 2, 188, 2, 208),
    ("2029-05-14", 3, 915, 2, 190, 1, 204),
    ("2029-05-21", 4, 925, 3, 195, 2, 210),
    ("2029-05-28", 3, 940, 5, 200, 1, 212),  # hardship regresses; overall still 3/940
]

# Ch39 packet fields carried into the weekly page (SIMULATED continuity).
PACKET = {
    "median_tte_days": 4.0,
    "tte_before_days": 19,
    "n_incidents_closed_to_eval": 3,
    "n_symptom_rejected": 1,
    "complaints_this_month": 31,
    "complaints_prev_month": 42,
    "sidebar_cases": 41,
    "inctoeval_digest": "810f8f17e55a",
}

# Decide-tier card for the report week (hardship wrong offers in rate-eligible sample).
DECIDE = {"name": "wrong_hardship_offer", "failures": 2, "n": 420, "target": 0.005}
GATE_FEE = {"name": "wrong_fee_explanation", "failures": 4, "n": 280, "target": 0.02}
MONITOR_TTE = {"name": "median_tte_days", "value": 4.0, "owner": "eval-lead"}
INFORM_CSAT = {"name": "complaint_count_month", "value": 31, "owner": "Rachel"}


def build():
    payload = {
        "seed": 2040,
        "label": "SIMULATED",
        "study_window": "2029-04-09 to 2029-05-28",
        "scoreboard_date": "2029-05-28",
        "weeks": WEEKS,
        "packet": PACKET,
        "decide": DECIDE,
        "gate_fee": GATE_FEE,
        "monitor_tte": MONITOR_TTE,
        "inform_csat": INFORM_CSAT,
        "segment_name": "hardship",
        "overall_ok_if_delta_le": 0.0,
        "segment_bad_if_delta_ge": 0.01,
    }
    raw = json.dumps(payload, sort_keys=True).encode()
    payload["digest"] = hashlib.sha256(raw).hexdigest()[:12]
    OUT.mkdir(exist_ok=True)
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2))
    print(payload["digest"], len(WEEKS))
    return payload


if __name__ == "__main__":
    build()
