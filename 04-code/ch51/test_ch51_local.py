from pathlib import Path
import json, subprocess

ROOT = Path(__file__).parent


def _run():
    subprocess.check_call(["bash", str(ROOT / "run_all.sh")], cwd=ROOT)


def test_run_locks():
    _run()
    fix = json.loads((ROOT / "out" / "fixture.json").read_text())
    lab = json.loads((ROOT / "out" / "lab.json").read_text())
    assert fix["seed"] == 2051 and fix["digest"] == "731ae5d6148e"
    assert lab["record"]["record_sha12"] == "443c07184ea1"
    assert lab["digest"] == "731ae5d6148e"
    assert fix["SIMULATED"] is True


def test_taxonomy_nontranslate_injection():
    _run()
    inj = json.loads((ROOT / "out" / "inject.json").read_text())
    assert inj["foreign"]["verdict"] == "HOLD_TAXONOMY_NONTRANSLATE"
    assert len(inj["foreign"]["foreign_labels"]) == 5
    assert inj["native_control"]["verdict"] == "TAXONOMY_OK"


def test_toronto_offline_online_gap():
    _run()
    ep = json.loads((ROOT / "out" / "lab.json").read_text())["evidence_pack"]
    assert ep["offline"]["sliced_by_cycle_day"] is False
    assert ep["offline"]["BillingCycleEdge_card"] is False
    assert ep["online"]["complaints"] >= 1
    assert ep["online"]["root_cause"] == "offline_taxonomy_missing_BillingCycleEdge"


def test_ch16_kinds_immutable():
    _run()
    ch = json.loads((ROOT / "out" / "lab.json").read_text())["evidence_pack"]["CH16"]
    assert ch["usage_incurred_usd"] == 6.191862
    assert ch["uncertain_reserve_usd"] == 0.050079
    assert ch["policy_headroom_usd"] == 0.05
    assert abs(ch["ceiling_usd"] - 6.291941) < 1e-9


def test_four_cases_and_borrow():
    _run()
    fix = json.loads((ROOT / "out" / "fixture.json").read_text())
    assert set(fix["cases"]) == {"hartford", "manchester", "toronto", "frankfurt"}
    assert fix["cases"]["toronto"]["failed_practice"] is True
    assert len(fix["harbor_borrow"]) == 4


def test_output_declares_simulated():
    _run()
    txt = (ROOT / "OUTPUT.txt").read_text()
    assert "SIMULATED" in txt and "731ae5d6148e" in txt and "PENDING" in txt
    assert "HOLD_TAXONOMY_NONTRANSLATE" in json.loads((ROOT / "out" / "inject.json").read_text())["foreign"]["verdict"]


def test_digest_reproducible():
    subprocess.check_call(["python3", str(ROOT / "fixture.py")], cwd=ROOT)
    d1 = json.loads((ROOT / "out" / "fixture.json").read_text())["digest"]
    subprocess.check_call(["python3", str(ROOT / "fixture.py")], cwd=ROOT)
    d2 = json.loads((ROOT / "out" / "fixture.json").read_text())["digest"]
    assert d1 == d2 == "731ae5d6148e"


def test_force_include_plan():
    _run()
    t = json.loads((ROOT / "out" / "try_its.json").read_text())
    assert t["action"] == "FORCE_INCLUDE_CYCLE_DAY_TRACES"
    assert "card_for_missing_class" in t["refuse_ship_until"]
