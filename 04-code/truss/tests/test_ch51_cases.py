from pathlib import Path
import json, subprocess

ROOT = Path(__file__).resolve().parents[2] / "ch51"


def test_ch51_lab_witness():
    subprocess.check_call(["bash", str(ROOT / "run_all.sh")], cwd=ROOT)
    lab = json.loads((ROOT / "out" / "lab.json").read_text())
    inj = json.loads((ROOT / "out" / "inject.json").read_text())
    assert lab["digest"] == "731ae5d6148e"
    assert lab["record"]["record_sha12"] == "443c07184ea1"
    assert inj["foreign"]["verdict"] == "HOLD_TAXONOMY_NONTRANSLATE"
    assert lab["evidence_pack"]["CH16"]["ceiling_usd"] == 6.291941
