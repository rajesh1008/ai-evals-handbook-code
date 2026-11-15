"""Local Ch50 tests: digest, lint-pass+unvalidated HOLD inject, SIM/PENDING."""
from __future__ import annotations
import json, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
DIGEST = "b261d8b6093e"
RECORD = "3f7a1b60bfc0"


@pytest.fixture(scope="module", autouse=True)
def _run():
    subprocess.check_call(["bash", str(ROOT / "run_all.sh")], cwd=str(ROOT))


def test_fixture_digest_sim():
    fix = json.loads((OUT / "fixture.json").read_text())
    assert fix["digest"] == DIGEST
    assert fix["SIMULATED"] is True
    assert fix["n_configs"] == 3
    assert fix["seed"] == 2050


def test_lab_record_and_inject():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["record"]["record_sha12"] == RECORD
    assert lab["digest"] == DIGEST
    ep = lab["evidence_pack"]
    assert ep["inject_caught"] is True
    assert ep["inject_lint_pass"] is True
    assert ep["inject_gate"] == "HOLD"
    assert ep["inject_reason"] == "unvalidated_judge"
    assert ep["live_provider_eval_sweeps"] == "PENDING"
    assert ep["paid_calls"] is False
    assert ep["ch16_ceiling_sum"] == 6.291941


def test_inject_caught():
    inj = json.loads((OUT / "inject.json").read_text())
    assert inj["caught"] is True
    assert inj["failure"] == "config_lints_clean_but_unvalidated_judge_gates_release"


def test_harbor_config_passes():
    lab = json.loads((OUT / "lab.json").read_text())
    by = {r["lint"]["config"]: r for r in lab["evidence_pack"]["rows"]}
    assert by["harbor_compass_v3"]["lint"]["lint_pass"] is True
    assert by["harbor_compass_v3"]["gate"]["gate_result"] == "PASS"
    assert by["missing_population"]["lint"]["lint_pass"] is False


def test_try_its():
    t = json.loads((OUT / "try_its.json").read_text())
    assert t["validate_judge_then_pass"]["gate"] == "PASS"
    assert t["short_digest_lint_hold"]["lint_pass"] is False
    assert t["monitor_still_holds_unvalidated"]["gate"] == "HOLD"


def test_output_spine():
    text = (ROOT / "OUTPUT.txt").read_text()
    assert DIGEST in text and RECORD in text
    assert "SIMULATED" in text and "PENDING" in text
    assert "inject_caught=True" in text
