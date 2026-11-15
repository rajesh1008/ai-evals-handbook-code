from datetime import date
from decimal import Decimal

from truss import checks as K


def test_outcomes_and_needs_propagate_cannot_tell():
    a = K.Verifier("A", "a", lambda t, up: K.Result(K.FAIL, "bad"))
    b = K.Verifier("B", "b", lambda t, up: K.Result(K.PASS, "ok"), needs=("A",))
    c = K.Verifier("C", "c", lambda t, up: K.Result(K.PASS, "ok"), applies=lambda t: False)
    s = K.Suite([b, a, c])
    assert [v for v in s.order] == ["A", "B", "C"]
    r = s.run({"trace_id": "t"})
    assert r["B"].outcome == K.CANNOT and "upstream A" in r["B"].evidence
    assert r["C"].outcome == K.NA
    assert K.verdict(r) == K.FAIL


def test_schema_subset():
    sch = {"type": "object", "required": ["x"], "additionalProperties": False,
           "properties": {"x": {"type": "integer", "minimum": 1, "maximum": 3}}}
    assert K.validate({"x": 2}, sch) == []
    assert K.validate({"x": 4}, sch)
    assert K.validate({"x": "2"}, sch)
    assert K.validate({}, sch)
    assert K.validate({"x": 1, "y": 0}, sch)


def test_extraction():
    assert K.money("pay $1,234.50 or $25") == [Decimal("1234.50"), Decimal("25")]
    assert K.dates("good through April 12, 2027 or 04/13/2027") == [date(2027, 4, 12), date(2027, 4, 13)]
    assert K.dates("hasta el 12 de abril de 2027") == [date(2027, 4, 12)]


def test_day_count_and_rounding():
    assert K.days_between(date(2027, 1, 31), date(2027, 3, 1), "30/360") == 31
    assert K.days_between(date(2027, 1, 31), date(2027, 3, 1), "actual/365") == 29
    assert K.cents(Decimal("0.125")) == Decimal("0.13")
    assert K.per_diem(36500, 0.10, "actual/365") == Decimal("10")
    assert K.per_diem(36000, 0.10, "actual/360") == Decimal("10")


def test_calendar_window_is_inclusive_and_month_end_clamped():
    assert K.within_months(date(2026, 4, 5), date(2027, 4, 5), 12)
    assert not K.within_months(date(2026, 4, 4), date(2027, 4, 5), 12)
    assert K.within_months(date(2027, 3, 1), date(2028, 3, 1), 12)          # 366 days, still inside
    assert K.months_before(date(2027, 3, 31), 1) == date(2027, 2, 28)


def test_precision_recall_and_mutation_score():
    pr = K.precision_recall({"a", "b"}, {"a", "c", "d"}, {"a", "c"})
    assert pr["precision"] == (1, 2) and pr["recall"] == (1, 2)
    v = K.Verifier("V", "v", lambda t, up: K.Result(K.FAIL if t["x"] > 0 else K.PASS, ""))
    sc = K.mutation_score(v, [{"trace_id": "t", "x": 0}], {"plus": lambda t: {**t, "x": 1}, "none": lambda t: None})
    assert sc["plus"]["killed"] == 1 and sc["none"]["applied"] == 0
