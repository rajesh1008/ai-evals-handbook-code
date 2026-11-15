from pathlib import Path
import json, subprocess

ROOT = Path(__file__).parent


def _run():
    subprocess.check_call(["bash", str(ROOT / "run_all.sh")], cwd=ROOT)


def test_run_locks():
    _run()
    fix = json.loads((ROOT / "out" / "fixture.json").read_text())
    lab = json.loads((ROOT / "out" / "lab.json").read_text())
    assert fix["seed"] == 2049 and fix["digest"] == "9aa91eeb5d57"
    assert lab["record"]["record_sha12"] == "7fe834b5e830"
    assert lab["digest"] == "9aa91eeb5d57"
    assert fix["SIMULATED"] is True


def test_dual_pin_injection():
    _run()
    inj = json.loads((ROOT / "out" / "inject.json").read_text())
    assert inj["dual"]["dual_change"] is True
    assert inj["dual"]["verdict"] == "HOLD_DUAL_PIN"
    assert inj["single"]["verdict"] == "HOLD_SINGLE_PIN"


def test_rollback_month_eleven():
    _run()
    lab = json.loads((ROOT / "out" / "lab.json").read_text())
    assert lab["evidence_pack"]["scoreboard"]["rollback_months"] == [11]
    assert lab["evidence_pack"]["rollback"]["action"] == "ROLLBACK_WITHIN_72H"


def test_ch16_kinds_immutable():
    _run()
    ch = json.loads((ROOT / "out" / "lab.json").read_text())["evidence_pack"]["CH16"]
    assert ch["usage_incurred_usd"] == 6.191862
    assert ch["uncertain_reserve_usd"] == 0.050079
    assert ch["policy_headroom_usd"] == 0.05
    assert abs(ch["ceiling_usd"] - 6.291941) < 1e-9


def test_pending_and_sidebar():
    _run()
    ep = json.loads((ROOT / "out" / "lab.json").read_text())["evidence_pack"]
    assert ep["live_provider_sweeps"] == "PENDING"
    assert ep["sidebar_q2_judge_skipped"]["executed"] is False
    assert ep["calendar_rows"] == 12


def test_digest_reproducible():
    subprocess.check_call(["python3", str(ROOT / "fixture.py")], cwd=ROOT)
    d1 = json.loads((ROOT / "out" / "fixture.json").read_text())["digest"]
    subprocess.check_call(["python3", str(ROOT / "fixture.py")], cwd=ROOT)
    d2 = json.loads((ROOT / "out" / "fixture.json").read_text())["digest"]
    assert d1 == d2 == "9aa91eeb5d57"


def test_upgrade_ticket_shadow():
    _run()
    t = json.loads((ROOT / "out" / "try_its.json").read_text())
    assert t["shadow_hours_required"] == 72
    assert "gold_freeze" in t["refuse_if_missing"]


def test_output_declares_simulated():
    _run()
    txt = (ROOT / "OUTPUT.txt").read_text()
    assert "SIMULATED" in txt and "9aa91eeb5d57" in txt and "PENDING" in txt
