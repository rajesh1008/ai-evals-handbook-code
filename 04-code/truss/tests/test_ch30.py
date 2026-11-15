from truss.gateway import (
    pin_record, migration_delta, release_decision, midrun_upgrade_detect,
    silent_change_score, deprecation_plan, judge_revalidation_triggers,
)
from truss import __version__

def test_version_floor():
    assert int(__version__.split(".")[1]) >= 33 or __version__.startswith("0.3")  # allow if parallel higher oddly
    # strongest: minor >= 33 when we own gateway
    parts = list(map(int, __version__.split(".")))
    assert parts >= [0, 33, 0]

def test_migration_and_hold():
    d = migration_delta({"a": 0.8, "b": 0.5}, {"a": 0.85, "b": 0.4})
    assert d["n_improved"] == 1 and d["n_regressed"] == 1
    dec = release_decision(d["rows"])
    assert dec["decision"] == "HOLD"

def test_midrun_and_silent():
    assert midrun_upgrade_detect(["m1", "m1", "m2"])["midrun_upgrade"]
    s = silent_change_score([{"label": "c1", "score": 1}, {"label": "c1", "score": 0}])
    assert s["n_flip"] == 1

def test_deprecation_and_triggers():
    assert deprecation_plan(60, True, False)["accept_cutover"]
    assert not deprecation_plan(30, True, False)["accept_cutover"]
    tr = judge_revalidation_triggers(True, False, False, 0.1)
    assert tr["must_revalidate"] and "model" in tr["triggers"]

def test_pin():
    p = pin_record("compass-llm-2028-09", "gateway", "2028-09-01", "abc")
    assert p["model_id"].startswith("compass")
