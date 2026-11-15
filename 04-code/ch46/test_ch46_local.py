from pathlib import Path
import json, subprocess, hashlib
import sys

HERE = Path(__file__).parent


def run_lab():
    subprocess.check_call(["bash", str(HERE / "run_all.sh")], cwd=HERE)


def test_run_and_digests():
    run_lab()
    lab = json.loads((HERE / "out/lab.json").read_text())
    inj = json.loads((HERE / "out/inject.json").read_text())
    fix = json.loads((HERE / "out/fixture.json").read_text())
    assert lab["kind"] == "SIMULATED"
    assert fix["ch45_digest_ref"] == "af63808723f1"
    assert fix["ch45_record_ref"] == "3d4c15e44e50"
    assert len(lab["artefact_order"]) == 8
    assert inj["caught"] is True
    assert inj["mismatch_count"] >= 1
    assert lab["returned_artefact"]["id"] == "A4_outcome_analysis"
    text = (HERE / "OUTPUT.txt").read_text()
    assert "metric_drift_caught=True" in text
    assert "sr26_2_genai_excluded=True" in text
    assert "live_pending=PENDING" in text


def test_second_person_table_sha_stable():
    run_lab()
    lab = json.loads((HERE / "out/lab.json").read_text())
    table = lab["reproduce_table"]
    raw = json.dumps(table, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(raw).hexdigest()[:12] == lab["table_sha12"]


def test_pack_metric_unit_is_offer():
    run_lab()
    fix = json.loads((HERE / "out/fixture.json").read_text())
    assert fix["pack_metric"]["unit"] == "offer"
    assert fix["dashboard_metric_drift"]["unit"] == "conversation"


def test_wilson_open_pre_post():
    run_lab()
    a4 = json.loads((HERE / "out/lab.json").read_text())["artefacts"]["A4_outcome_analysis"]
    assert a4["overall_pre"]["OPEN"] is True
    assert a4["overall_post"]["OPEN"] is True
    assert a4["overall_pre"]["k"] == 23
    assert a4["overall_post"]["k"] == 11


def test_no_invented_meets():
    run_lab()
    a4 = json.loads((HERE / "out/lab.json").read_text())["artefacts"]["A4_outcome_analysis"]
    assert "MEETS" not in a4["ship_language"] or "not MEETS" in a4["ship_language"]


def test_eight_artefacts_present():
    run_lab()
    lab = json.loads((HERE / "out/lab.json").read_text())
    for a in lab["artefact_order"]:
        assert a in lab["artefacts"]


def test_try_its_exist():
    run_lab()
    t = json.loads((HERE / "out/try_its.json").read_text())
    assert t["try_catch_metric_drift"]["actual_caught"] is True


def test_output_lines():
    run_lab()
    lines = (HERE / "OUTPUT.txt").read_text().strip().splitlines()
    assert len(lines) >= 8
