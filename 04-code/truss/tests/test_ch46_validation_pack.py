"""Truss suite witness for Ch46 validation pack lab."""
from pathlib import Path
import json, subprocess

ROOT = Path(__file__).resolve().parents[2] / "ch46"


def test_ch46_pack_drift_and_digests():
    subprocess.check_call(["bash", str(ROOT / "run_all.sh")], cwd=ROOT)
    lab = json.loads((ROOT / "out/lab.json").read_text())
    inj = json.loads((ROOT / "out/inject.json").read_text())
    assert lab["pack_sha12"]
    assert inj["caught"] is True
    assert lab["artefacts"]["A7_limitations_pending_scope"]["sr26_2_generative_agentic_excluded"] is True
    assert lab["artefacts"]["A4_outcome_analysis"]["overall_pre"]["k"] == 23
