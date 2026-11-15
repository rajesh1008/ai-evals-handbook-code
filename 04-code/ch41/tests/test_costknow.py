import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "truss"))
from truss.costknow import study_ceiling, waterfall, bias_battery_gate, amortise_study

OUT = Path(__file__).resolve().parents[1] / "out"

def test_ceiling():
    c = study_ceiling(6.191862, 0.050079, 0.05)
    assert abs(c["safe_ceiling_usd"] - 6.291941) < 1e-6

def test_waterfall_lab():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["waterfall"]["start_usd"] == 1900.0
    assert lab["waterfall"]["end_usd"] == 640.0
    assert lab["teaching"]["cheap_fails_bias"] is True

def test_inject_refuses():
    g = bias_battery_gate(tpr=0.92, tnr=0.91, position_flip_rate=0.18)
    assert g["admit"] is False

def test_amortise():
    a = amortise_study(6.191862, 12)
    assert a["amortised_per_release_usd"] == 6.191862 / 12
