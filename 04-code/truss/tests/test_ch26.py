from truss.multimodal import layer_outcome, field_match, degrade_effect, wer, drop_negative_amounts, voice_task_table
from truss import __version__

def test_version():
    maj, minor, *_ = __version__.split(".")
    assert int(maj) > 0 or int(minor) >= 29

def test_layers():
    r = layer_outcome(True, False, True)
    assert r["first_fail"] == "recognition" and not r["end_to_end_ok"]

def test_fields_and_degrade():
    fm = field_match({"a": 1.0}, {"a": 1.0}, ["a"])
    assert fm["rate"] == 1.0
    assert degrade_effect("glare", 1.0) < degrade_effect("clean", 1.0)

def test_wer():
    assert wer(["a","b"], ["a","b"]) == 0.0
    assert wer(["a","b"], ["a","c"]) == 0.5

def test_drop_neg():
    s = drop_negative_amounts("deduction -12.50 and (3.00)")
    assert "-12.50" not in s and "(3.00)" not in s

def test_voice_table():
    t = voice_task_table([{"wer": 0.0, "task_ok": False}, {"wer": 0.4, "task_ok": True}])
    assert t["low_wer_task_fail"] == 1 and t["high_wer_task_ok"] == 1

def test_fixture():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "ch26" / "out" / "fixture.json"
    if not p.exists():
        return
    d = json.loads(p.read_text())
    assert d["n_docs"] == 100 and d["n_voice"] == 40
