"""Truss witness: Ch49 twelve-month lab locks."""
from pathlib import Path
import json, subprocess

ROOT = Path(__file__).resolve().parents[2] / "ch49"


def test_ch49_lab_witness():
    subprocess.check_call(["bash", str(ROOT / "run_all.sh")], cwd=ROOT)
    lab = json.loads((ROOT / "out" / "lab.json").read_text())
    assert lab["digest"] == "9aa91eeb5d57"
    assert lab["record"]["record_sha12"] == "7fe834b5e830"
    assert lab["evidence_pack"]["pin_diff"]["verdict"] == "HOLD_DUAL_PIN"
    assert lab["SIMULATED"] is True
