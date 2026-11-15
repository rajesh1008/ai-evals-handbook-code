"""Local Ch45 tests locking fixture digests, Wilson cards, proxy, try_its, boundaries."""
from __future__ import annotations
import json, math, subprocess, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
sys.path.insert(0, str(ROOT.parents[0] / "truss"))
from truss.rates import wilson

DIGEST = "af63808723f1"
RECORD = "3d4c15e44e50"
TARGET = 0.005


@pytest.fixture(scope="module", autouse=True)
def _run_lab():
    subprocess.check_call(["bash", str(ROOT / "run_all.sh")], cwd=str(ROOT))


def test_fixture_digest_sim_n_seed():
    fix = json.loads((OUT / "fixture.json").read_text())
    assert fix["digest"] == DIGEST
    assert fix["seed"] == 2045
    assert fix["n"] == 2400
    assert len(fix["rows"]) == 2400
    assert fix["SIMULATED"] is True
    assert fix["illegal_proxy_field"] == "affinity_bucket"
    assert len(fix["legitimate_segments"]) == 6


def test_lab_record_pre_post_overall_open():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["record"]["record_sha12"] == RECORD
    assert lab["record"]["digest"] == DIGEST
    assert lab["SIMULATED"] is True
    ep = lab["evidence_pack"]
    pre, post = ep["pre_overall"], ep["post_overall"]
    assert pre["k"] == 23 and pre["n"] == 2400
    assert post["k"] == 11 and post["n"] == 2400
    assert pre["OPEN"] is True and post["OPEN"] is True
    assert pre["wilson_hi"] >= TARGET and post["wilson_hi"] >= TARGET
    _, pre_hi = wilson(23, 2400)
    _, post_hi = wilson(11, 2400)
    assert pre["wilson_hi"] == pytest.approx(pre_hi)
    assert post["wilson_hi"] == pytest.approx(post_hi)


def test_hot_phone_signature_pre_post():
    lab = json.loads((OUT / "lab.json").read_text())
    ep = lab["evidence_pack"]
    hot_pre = ep["hot_segment_pre"]
    hot_post = ep["hot_segment_post"]
    assert hot_pre["segment"] == "phone×signature"
    assert hot_post["segment"] == "phone×signature"
    assert hot_pre["k"] == 14 and hot_pre["n"] == 400
    assert hot_post["k"] == 2 and hot_post["n"] == 400
    assert hot_pre["OPEN"] is True
    assert hot_pre["wilson_hi"] > hot_post["wilson_hi"]
    assert hot_pre["wilson_hi"] == pytest.approx(wilson(14, 400)[1])
    assert hot_post["wilson_hi"] == pytest.approx(wilson(2, 400)[1])


def test_proxy_caught_and_disjoint():
    inj = json.loads((OUT / "inject.json").read_text())
    assert inj["caught"] is True
    assert inj["illegal_proxy"] == "affinity_bucket"
    assert inj["legit_disjoint_from_proxy"] is True
    lab = json.loads((OUT / "lab.json").read_text())
    proxy = lab["proxy_injection"]
    assert proxy["caught"] is True
    assert proxy["field"] == "affinity_bucket"
    legit = set(lab["evidence_pack"]["legitimate_strata"])
    proxy_labels = {c["segment"] for c in proxy["cards_must_not_decide"]}
    assert legit.isdisjoint(proxy_labels)


def test_try_its_trophy_witness():
    try_its = json.loads((OUT / "try_its.json").read_text())
    assert try_its["declared_segments"] == 6
    assert try_its["hidden_OPEN"] == 6
    assert try_its["visible_if_trophy"] == 0
    assert "trophy" in try_its["refuse"].lower() or "hiding" in try_its["refuse"].lower()


def test_output_txt_spine():
    text = (ROOT / "OUTPUT.txt").read_text()
    assert DIGEST in text
    assert "SIMULATED" in text
    assert "OPEN=True" in text
    assert "proxy_caught=True" in text
    assert RECORD in text
    assert "phone×signature" in text or "phone" in text


def test_wrong_input_boundaries():
    from lab import segment_card, overall, adverse_ratio
    # empty population must not silently invent a rate
    with pytest.raises(ZeroDivisionError):
        overall([], "wrong_offer_pre")
    assert segment_card([], "wrong_offer_pre", "segment") == []
    rows = [{"wrong_offer_pre": 0, "segment": "web×compass", "affinity_bucket": "affinity_A"}]
    ov = overall(rows, "wrong_offer_pre")
    assert ov["n"] == 1 and ov["k"] == 0 and ov["OPEN"] is True  # wilson hi on 0/1 > 0.5%
    cards = [{"segment": "web×compass", "rate": 0.0}, {"segment": "phone×signature", "rate": 0.01}]
    ratios = adverse_ratio(cards, "web×compass")
    assert len(ratios) == 2
    assert math.isnan(ratios[1]["ratio_vs_baseline"])
    with pytest.raises(KeyError):
        overall(rows, "missing_field")


def test_pending_live_not_executed_in_lab():
    """Live provider fairness batteries are not present as measured rates in the lab."""
    lab = json.loads((OUT / "lab.json").read_text())
    blob = json.dumps(lab)
    assert "live_provider_rate" not in blob
    assert lab["SIMULATED"] is True
    # Manuscript marks PENDING; lab must stay SIM-only
    assert "af63808723f1" in blob
