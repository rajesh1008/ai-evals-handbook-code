"""Chapter 11 tests: the field scorer (Truss 0.14)."""
from datetime import date

from truss import fields as F

GROSS = F.FieldSpec("gross_pay", "money", frozenset({"pay_stub"}), critical=True)
EMP = F.FieldSpec("employer", "name", match="prefix")


def test_money_and_date_normalisers_are_format_only():
    assert F.money("$1,234.50") == 1234.5 and F.money(1234.5) == 1234.5
    assert F.to_date("12 de abril de 2027") == date(2027, 4, 12) == F.to_date("Apr 12, 2027") == F.to_date("04/12/2027")
    try:
        F.money("$l,234.50")          # OCR letter: the scorer must not repair it
        assert False
    except ValueError:
        pass


def test_five_outcomes():
    assert F.outcome(GROSS, "$2,187.50", 2187.5) == "tp"
    assert F.outcome(GROSS, 2187.0, 2187.5) == "wrong"
    assert F.outcome(GROSS, None, 2187.5) == "miss"
    assert F.outcome(GROSS, 100.0, None) == "invented"
    assert F.outcome(GROSS, None, None) == "tn"


def test_names_fold_accents_suffixes_and_truncation():
    assert F.outcome(F.FieldSpec("person_name", "name"), "María González", "Maria Gonzalez") == "tp"
    assert F.outcome(EMP, "Agua Fria Landscaping Co.", "Agua Fria Landscaping") == "tp"
    assert F.outcome(EMP, "CHANDLER PRECISION M", "Chandler Precision Machining") == "tp"
    assert F.outcome(EMP, "Chandler Plumbing", "Chandler Precision Machining") == "wrong"


def test_precision_recall_ignore_true_negatives():
    t = F.field_table([("f", "tp")] * 8 + [("f", "wrong"), ("f", "invented")] + [("f", "tn")] * 90)
    assert t["f"]["precision"] == 0.8 and abs(t["f"]["recall"] - 8 / 9) < 1e-9 and t["f"]["accuracy"] == 0.98


def test_rows_and_layer_one():
    gold = [{"date": "2027-03-03", "amount": 1252.45}, {"date": "2027-03-10", "amount": 1252.80}]
    pred = [{"date": "2027-03-03", "amount": 1252.45}, {"date": "2027-03-19", "amount": 149.80}]
    assert F.match_rows(pred, gold) == {"tp": 1, "extra": 1, "missed": 1, "duplicates": 0}
    specs = [GROSS, F.FieldSpec("doc_type", "enum", allowed=("pay_stub",))]
    r = F.layer_one({"doc_type": "pay_stub", "gross_pay": None, "bonus": 1}, specs)
    assert r["required_missing"] == ["gross_pay"] and r["unknown"] == ["bonus"]


def test_identity_catches_a_rounding_normaliser():
    cases = [("$1,523.43", 1523.43), ("$2,187.50", 2187.5), ("$900.00", 900.0)]
    assert F.identity_test(F.money, cases) == []
    rounding = lambda s: float(round(F.money(s)))
    assert len(F.identity_test(rounding, cases)) == 2
    rows, ece = F.calibration([0.99, 0.99, 0.6, 0.6], [1, 0, 1, 0])
    assert abs(ece - 0.295) < 1e-9


def test_implausible_dates_flags_future_only():
    from truss.fields import implausible_dates
    assert implausible_dates({"period_end": "10/05/2027"}, "2027-05-14") == ["period_end"]   # read as 5 October
    assert implausible_dates({"period_end": "2027-01-05"}, "2027-05-17") == []               # wrong but possible
    assert implausible_dates({"period_end": None}, "2027-05-17") == []
