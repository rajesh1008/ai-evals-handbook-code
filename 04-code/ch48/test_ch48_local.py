"""Local Ch48 tests: digest, vocab-reward inject, SIM/PENDING."""
from __future__ import annotations
import json, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
DIGEST = "9a9d842a198b"
RECORD = "9f17e678e998"


@pytest.fixture(scope="module", autouse=True)
def _run():
    subprocess.check_call(["bash", str(ROOT / "run_all.sh")], cwd=str(ROOT))


def test_fixture_digest_sim():
    fix = json.loads((OUT / "fixture.json").read_text())
    assert fix["digest"] == DIGEST
    assert fix["SIMULATED"] is True
    assert fix["n_traces"] == 8
    assert fix["seed"] == 2048


def test_lab_record_and_inversion():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["record"]["record_sha12"] == RECORD
    assert lab["digest"] == DIGEST
    ep = lab["evidence_pack"]
    assert ep["inversion"] is True
    assert ep["winner_findings"] == "A"
    assert ep["winner_vocabulary"] == "B"
    assert ep["live_provider_eval_sweeps"] == "PENDING"
    assert ep["paid_calls"] is False


def test_inject_caught():
    inj = json.loads((OUT / "inject.json").read_text())
    assert inj["caught"] is True
    assert inj["failure"] == "rubric_rewards_vocabulary_over_findings"


def test_scores_locked():
    lab = json.loads((OUT / "lab.json").read_text())
    by = {r["candidate"]: r for r in lab["evidence_pack"]["rows"]}
    assert by["A"]["findings"]["score"] == 32
    assert by["B"]["findings"]["score"] == -10
    assert by["A"]["vocabulary"]["score"] == 14
    assert by["B"]["vocabulary"]["score"] == 59


def test_try_its_coaching():
    t = json.loads((OUT / "try_its.json").read_text())
    assert t["coached_B_findings"]["s1_hits"] == 2
    assert t["trophy"]["planted_hits_b"] == 0


def test_output_spine():
    text = (ROOT / "OUTPUT.txt").read_text()
    assert DIGEST in text and RECORD in text
    assert "SIMULATED" in text and "PENDING" in text
    assert "inversion=True" in text
