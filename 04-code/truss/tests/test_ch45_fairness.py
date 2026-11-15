"""Ch45 offline fairness lab tests."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "ch45"


def test_run_all_and_invariants():
    subprocess.check_call(["bash", str(CH / "run_all.sh")], cwd=CH)
    fix = json.loads((CH / "out" / "fixture.json").read_text())
    lab = json.loads((CH / "out" / "lab.json").read_text())
    inj = json.loads((CH / "out" / "inject.json").read_text())
    assert fix["n"] == 2400
    assert fix["SIMULATED"] is True
    assert fix["digest"] == "af63808723f1"
    assert lab["record"]["record_sha12"] == "3d4c15e44e50"
    assert lab["evidence_pack"]["hot_segment_pre"]["segment"] == "phone×signature"
    assert lab["evidence_pack"]["hot_segment_pre"]["wilson_hi"] > 0.005
    assert lab["evidence_pack"]["hot_segment_post"]["wilson_hi"] < lab["evidence_pack"]["hot_segment_pre"]["wilson_hi"]
    assert inj["caught"] is True
    assert inj["illegal_proxy"] == "affinity_bucket"
    # digest stable
    subprocess.check_call([sys.executable, str(CH / "fixture.py")], cwd=CH)
    fix2 = json.loads((CH / "out" / "fixture.json").read_text())
    assert fix2["digest"] == fix["digest"]
