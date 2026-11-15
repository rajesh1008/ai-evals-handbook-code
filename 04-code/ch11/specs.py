"""Chapter 11: the field specification for hardship income extraction (guideline v3)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.fields import FieldSpec  # noqa: E402

ALL = frozenset({"pay_stub", "bank_statement", "hardship_letter"})
STUB, BANK, LETTER = frozenset({"pay_stub"}), frozenset({"bank_statement"}), frozenset({"hardship_letter"})
CENT = 0.005
SPECS = [
    FieldSpec("doc_type", "enum", ALL, critical=True, allowed=("pay_stub", "bank_statement", "hardship_letter")),
    FieldSpec("person_name", "name", ALL),
    FieldSpec("employer", "name", STUB | BANK, match="prefix"),
    FieldSpec("period_end", "date", ALL, critical=True),
    FieldSpec("pay_frequency", "enum", STUB, critical=True, allowed=("weekly", "biweekly", "semimonthly", "monthly")),
    FieldSpec("gross_pay", "money", STUB, critical=True, tolerance=CENT),
    FieldSpec("net_pay", "money", STUB, tolerance=CENT),
    FieldSpec("ytd_gross", "money", STUB, tolerance=CENT),
    FieldSpec("payroll_total", "money", BANK, critical=True, tolerance=CENT),
    FieldSpec("stated_monthly_income", "money", frozenset(), critical=True, tolerance=CENT),
    FieldSpec("loan_last4", "id", LETTER, critical=True),
    FieldSpec("hardship_reason", "enum", LETTER, critical=True,
              allowed=("job_loss", "reduced_hours", "medical", "divorce_separation", "death_in_family", "disaster")),
]
BY = {s.name: s for s in SPECS}
FIELDS = [s.name for s in SPECS]
CRITICAL = [s.name for s in SPECS if s.critical]
# which fields each document type can carry (the cells of the heat map)
APPLIES = {"pay_stub": ["doc_type", "person_name", "employer", "period_end", "pay_frequency", "gross_pay", "net_pay", "ytd_gross"],
           "bank_statement": ["doc_type", "person_name", "employer", "period_end", "payroll_total"],
           "hardship_letter": ["doc_type", "person_name", "employer", "period_end", "stated_monthly_income", "loan_last4",
                               "hardship_reason"]}
PER_YEAR = {"weekly": 52, "biweekly": 26, "semimonthly": 24, "monthly": 12}
