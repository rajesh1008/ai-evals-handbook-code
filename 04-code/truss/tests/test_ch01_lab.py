import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ch01"))
from replay import (check_manifest, flipped, open_store, pass_at_k,  # noqa: E402
                    pass_hat_k, pick_conversations, replay, wilson)


@pytest.fixture(scope="module")
def convs():
    return pick_conversations(open_store())


def test_temperature_zero_is_repeatable(convs):
    assert flipped(replay(convs, runs=3, temperature=0.0)) == []


def test_production_run_matches_chapter(convs, monkeypatch):
    monkeypatch.delenv("COMPASS_TEMPERATURE", raising=False)
    res = replay(convs, runs=3)
    assert len(flipped(res)) == 3
    assert pass_at_k(res, 3) >= pass_hat_k(res, 3)


def test_manifest_rejects_mixed_temperatures(convs, monkeypatch):
    monkeypatch.setenv("COMPASS_TEMPERATURE", "0")
    a = replay(convs, runs=1)
    monkeypatch.delenv("COMPASS_TEMPERATURE")
    b = replay(convs, runs=1)
    with pytest.raises(ValueError):
        check_manifest({t: a[t] + b[t] for t in a})


def test_wilson_on_twenty():
    lo, hi = wilson(20, 20)
    assert round(lo, 2) == 0.84 and hi == 1.0
