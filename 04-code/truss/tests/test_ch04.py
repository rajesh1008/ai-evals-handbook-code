"""Chapter 4: layers, stages, costs and the placement lint."""
import pytest

from truss.layers import Check, Cost, Suite, lint, monthly_bill, summarise

PRICES = {"input_per_m": 3.0, "output_per_m": 15.0, "runner_per_min": 0.008}


def test_cost_adds_model_people_and_machine():
    c = Cost(input_tokens=1_000_000, output_tokens=100_000, human_minutes=6, human_rate=60, cpu_seconds=60)
    assert c.dollars(1, PRICES) == pytest.approx(3.0 + 1.5 + 6.0 + 0.008)
    assert Cost().dollars(1000, PRICES) == 0


def test_check_validates_layer_stream_stage():
    with pytest.raises(ValueError):
        Check("x", 6, "code tests", "me", ("commit",))
    with pytest.raises(ValueError):
        Check("x", 1, "vibes", "me", ("commit",))
    with pytest.raises(ValueError):
        Check("x", 1, "code tests", "me", ("nightly",))


def test_run_is_lowest_layer_first_and_fails_fast():
    S = Suite(PRICES)
    calls = []

    @S.check("judge", 3, "judge evals", "lead", ("release",), Cost(input_tokens=1000))
    def _(ctx):
        calls.append("judge")
        return 10, 0, ""

    @S.check("unit", 1, "code tests", "ryan", ("release",))
    def _(ctx):
        calls.append("unit")
        return 3, 1, "boom"

    res = S.run("release", {})
    assert calls == ["unit"] and len(res) == 1 and not res[0].passed
    res = S.run("release", {}, fail_fast=False)
    assert calls[-2:] == ["unit", "judge"]
    assert summarise(res)[3]["dollars"] == pytest.approx(10 * 1000 * 3 / 1e6)


def test_lint_flags_judge_at_commit():
    S = Suite(PRICES)
    S.add(Check("fee rule", 1, "code tests", "ryan", ("commit",)))
    assert lint(S) == []
    S.add(Check("judge", 3, "judge evals", "ryan", ("commit",)))
    problems = lint(S)
    assert len(problems) == 2 and all(p.startswith("judge") for p in problems)
    S.add(Check("router fixture", 2, "component evals", "ryan", ("commit",)))
    assert any("router fixture" in p for p in lint(S))


def test_monthly_bill_scales_with_stage_frequency():
    S = Suite(PRICES)
    S.add(Check("read", 3, "human review", "grace", ("release",), cost=Cost(human_minutes=10, human_rate=60)))
    bill = monthly_bill(S, {"release": 2}, {"read": 100})
    assert bill[3] == pytest.approx(2000) and bill[1] == 0


def test_duplicate_names_refused():
    S = Suite(PRICES)
    S.add(Check("a", 1, "code tests", "r", ("commit",)))
    with pytest.raises(ValueError):
        S.add(Check("a", 1, "code tests", "r", ("commit",)))
