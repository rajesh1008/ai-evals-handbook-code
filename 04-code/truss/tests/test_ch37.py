from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "truss"))
from truss.guardmon import (
    promote_check_to_guard,
    evaluate_guard,
    latency_breaks_channel,
    vocabulary_overrefuse,
    hardship_guard_coverage,
)

OUT = ROOT / "ch37" / "out"


def test_promote_two_guards():
    g1 = promote_check_to_guard("hardship_eligibility_schema", latency_budget_ms=80)
    g2 = promote_check_to_guard("fee_amount_parse", latency_budget_ms=60)
    assert g1["promoted"] and g2["tier"] == "in_flight"


def test_sms_break():
    r = latency_breaks_channel(2400, channel_timeout_ms=2000)
    assert r["breaks_timeout"] and r["label"] == "SMS_TIMEOUT_BREAK"


def test_metrics_and_vocab():
    lab = json.loads((OUT / "lab.json").read_text())
    m = lab["metrics"]
    assert m["n"] == 1200
    assert 0 < m["precision"] <= 1
    assert m["over_block_rate"] > 0
    assert lab["vocabulary"]["n_overrefuse"] >= 1


def test_hardship_100():
    c = hardship_guard_coverage(480, 480)
    assert c["meets_100pct"]


def test_lab_teaching_flags():
    lab = json.loads((OUT / "lab.json").read_text())
    inj = json.loads((OUT / "inject.json").read_text())
    assert lab["teaching"]["two_checks_promoted"]
    assert lab["teaching"]["hardship_100pct"]
    assert inj["caught"]
