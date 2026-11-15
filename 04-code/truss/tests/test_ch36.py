from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from truss.liveexp import assign_unit, refine_guardrail, interleave_rankings

OUT = ROOT / "ch36" / "out"

def test_digest_and_assignment():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["digest"] == "125f6221af44"
    assert lab["assignment"]["unit"] == "borrower"
    assert lab["assignment"]["n_control"] + lab["assignment"]["n_treatment"] == 200

def test_holiday_injection_stops_arm():
    inj = json.loads((OUT / "inject.json").read_text())
    assert inj["caught"] is True
    assert inj["arm_stopped"] == "treatment"
    assert inj["k_errors"] == 40
    assert inj["n"] == 140

def test_zero_errors_do_not_trip():
    g = refine_guardrail(0, 100, target=0.005)
    assert g["trip"] is False

def test_interleave_treatment_wins():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["interleave"]["winner"] == "treatment"
    assert lab["interleave"]["credit"]["treatment"] == 2

def test_assign_stable():
    assert assign_unit("b-900001", "harbor-hardship-ab-2028-11") == "treatment"
