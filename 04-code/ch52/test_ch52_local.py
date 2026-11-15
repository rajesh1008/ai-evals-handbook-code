"""Local tests for Ch52 hardening checklist lab."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "out"


def setup_module():
    subprocess.check_call([sys.executable, str(ROOT / "fixture.py")], cwd=ROOT)
    subprocess.check_call([sys.executable, str(ROOT / "lab.py")], cwd=ROOT)


def test_seed_and_digest():
    fix = json.loads((OUT / "fixture.json").read_text())
    assert fix["seed"] == 2052
    assert len(fix["digest"]) == 12


def test_inject_caught():
    lab = json.loads((OUT / "lab.json").read_text())
    ep = lab["evidence_pack"]
    assert ep["inject_caught"] is True
    assert ep["inject_finding"] == "JUDGE_VERSION_PINNED_NOWHERE"
    assert ep["inject_config"] == "compass_hardship_unpinned_judge"


def test_pinned_config_passes():
    lab = json.loads((OUT / "lab.json").read_text())
    by = {r["config"]: r for r in lab["evidence_pack"]["hardening_reports"]}
    assert by["compass_fee_v3_pinned"]["checklist_pass"] is True
    assert by["compass_hardship_unpinned_judge"]["checklist_pass"] is False


def test_ch16_kinds_immutable():
    lab = json.loads((OUT / "lab.json").read_text())
    ck = lab["evidence_pack"]["CH16"]
    assert ck["ceiling_sum_usd"] == 6.291941
    assert ck["known_incurred_usd"] == 6.191862
    assert ck["uncertain_reserve_usd"] == 0.050079
    assert ck["policy_headroom_usd"] == 0.05


def test_scoreboard_open_honest():
    lab = json.loads((OUT / "lab.json").read_text())
    v = lab["evidence_pack"]["scoreboard_verdict"]
    assert v["all_green"] is False
    assert v["open_targets"] >= 2


def test_no_paid_marker():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["evidence_pack"]["live_provider_sweeps"] == "PENDING"
    assert lab["evidence_pack"]["SIMULATED"] is True


def test_record_stable():
    lab = json.loads((OUT / "lab.json").read_text())
    assert len(lab["record"]["record_sha12"]) == 12
