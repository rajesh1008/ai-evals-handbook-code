"""Local Ch47 tests: digest, missed-incident inject, force-include, SIM/PENDING."""
from __future__ import annotations
import json, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
DIGEST = "6212aade9fb2"
RECORD = "6ae3ea143e20"


@pytest.fixture(scope="module", autouse=True)
def _run():
    subprocess.check_call(["bash", str(ROOT / "run_all.sh")], cwd=str(ROOT))


def test_fixture_digest_sim():
    fix = json.loads((OUT / "fixture.json").read_text())
    assert fix["digest"] == DIGEST
    assert fix["SIMULATED"] is True
    assert fix["n_week"] == 70
    assert fix["missed_incident_trace_id"] == "t-199847"
    assert fix["missed_incident_trace_id"] not in {r["trace_id"] for r in fix["rows"]}


def test_lab_record_and_hold():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["record"]["record_sha12"] == RECORD
    assert lab["digest"] == DIGEST
    ep = lab["evidence_pack"]
    assert ep["coverage"]["n_missed"] == 1
    assert ep["ritual"]["ship_verb"] == "HOLD"
    assert ep["live_provider_eval_sweeps"] == "PENDING"
    assert ep["SIMULATED"] is True


def test_inject_caught():
    inj = json.loads((OUT / "inject.json").read_text())
    assert inj["caught"] is True
    assert inj["missed_trace_id"] == "t-199847"
    assert inj["ship_blocked"] is True


def test_try_its_force_include_and_trophy():
    t = json.loads((OUT / "try_its.json").read_text())
    assert t["after_force_include_n_missed"] == 0
    assert t["after_force_include_ship"] == "SHIP_CANDIDATE"
    assert t["trophy"]["hidden_missed"] == 1


def test_output_spine():
    text = (ROOT / "OUTPUT.txt").read_text()
    assert DIGEST in text and RECORD in text
    assert "SIMULATED" in text and "PENDING" in text
    assert "HOLD" in text


def test_registry_has_owners_and_gates():
    lab = json.loads((OUT / "lab.json").read_text())
    reg = lab["evidence_pack"]["registry"]
    assert len(reg) >= 4
    assert all("owner" in r and "gate" in r for r in reg)
