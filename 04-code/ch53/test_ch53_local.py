"""Local tests for Ch53 SIMULATED lab."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def test_fixture_and_lab_exist():
    assert (OUT / "fixture.json").exists()
    assert (OUT / "lab.json").exists()
    assert (OUT / "OUTPUT.txt").exists()


def test_simulated_flags():
    fix = json.loads((OUT / "fixture.json").read_text())
    lab = json.loads((OUT / "lab.json").read_text())
    assert fix["SIMULATED"] is True
    assert lab["evidence_pack"]["SIMULATED"] is True
    assert fix["live_provider_comparison"] == "PENDING"
    assert fix["no_paid_calls"] is True


def test_inject_trajectory_catch_outcome_miss():
    lab = json.loads((OUT / "lab.json").read_text())["evidence_pack"]
    assert lab["inject_primary"] == "TRAJECTORY_CATCH_OUTCOME_MISS"
    assert lab["inject_case"] == "T17"
    assert lab["inject_caught"] is True
    for g in lab["gates"]:
        assert g["inject_caught_trajectory"] is True
        assert g["inject_missed_by_outcome"] is True
        assert "T17" in g["trajectory_fail_ids"]
        assert "T17" not in g["outcome_fail_ids"]


def test_two_gen_newer_present():
    lab = json.loads((OUT / "lab.json").read_text())["evidence_pack"]
    ids = {m["id"] for m in lab["models"]}
    assert ids == {"sim_gen_N", "sim_gen_N_plus_2"}
    gates = {g["model_id"]: g for g in lab["gates"]}
    # newer fixture improves outcome rate (T21) while T17 trajectory still fails both
    assert gates["sim_gen_N_plus_2"]["outcome_pass_rate"] > gates["sim_gen_N"]["outcome_pass_rate"]


def test_harbor_last_look_inherited():
    hl = json.loads((OUT / "lab.json").read_text())["evidence_pack"]["harbor_last_look"]
    assert hl["ch52_digest"] == "73ee6bb8ebe5"
    assert hl["ch52_record"] == "e93a7515e856"
    assert hl["ch52_seed"] == 2052
    assert hl["hardship_status"] == "OPEN"
    assert hl["fee_status"] == "OPEN"
    assert hl["rachel_share"] == "CONDITIONAL_10pct"
    assert hl["sarah_kinds"] == "MEETS_KINDS"


def test_ch16_kinds_immutable():
    ch16 = json.loads((OUT / "lab.json").read_text())["evidence_pack"]["CH16"]
    assert ch16["ceiling_sum_usd"] == 6.291941
    assert ch16["known_incurred_usd"] == 6.191862
    assert ch16["uncertain_reserve_usd"] == 0.050079
    assert ch16["policy_headroom_usd"] == 0.05


def test_digest_stable():
    fix = json.loads((OUT / "fixture.json").read_text())
    lab = json.loads((OUT / "lab.json").read_text())
    assert fix["digest"] == lab["digest"]
    assert len(fix["digest"]) == 12
