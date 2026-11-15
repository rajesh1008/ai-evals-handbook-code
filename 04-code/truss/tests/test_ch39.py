from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "truss"))
from truss.inctoeval import time_to_eval_days, symptom_vs_failure_mode, regression_case

OUT = ROOT / "ch39" / "out"


def test_tte():
    assert time_to_eval_days("2029-04-24", "2029-04-28") == 4


def test_symptom_injection():
    inj = json.loads((OUT / "inject.json").read_text())
    assert inj["caught"]
    assert not inj["diagnosis"]["usable_as_gate"]


def test_three_cases_and_tte_flag():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["teaching"]["three_incidents_to_cases"]
    assert lab["teaching"]["tte_19_to_4"]
    assert lab["median_tte_days"] == 4


def test_complaints_falling():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["weekly"]["complaints_falling"]


def test_fm_case_usable():
    c = regression_case("c", incident_id="i", failure_mode="FM-x", against="failure_mode", owner="o")
    assert symptom_vs_failure_mode(c)["usable_as_gate"]
