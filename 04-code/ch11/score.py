"""Chapter 11: shared scoring of one extraction run (used by lab.py, inject.py, try_its.py, figures)."""
from datetime import date
import docs as DOCS, extract as EX
from specs import SPECS, BY, FIELDS, CRITICAL, APPLIES, PER_YEAR
from truss import fields as F


def parsed(model):
    raw = EX.load(model)
    out = {}
    for i, r in raw.items():
        obj, repaired = F.parse_json(r["raw"])
        out[i] = {"obj": obj, "repaired": repaired, "raw": r["raw"]}
    return out


def value(obj, f):
    return None if obj is None else obj.get(f)


def outcomes(docs, ext, normaliser=None):
    """{doc: {field: outcome}}; normaliser (optional) is applied to every money value first."""
    res = {}
    for d in docs:
        obj = ext[d["id"]]["obj"]
        fo = {}
        for f in FIELDS:
            v = value(obj, f)
            if normaliser and BY[f].kind == "money" and v is not None:
                try:
                    v = normaliser(v)
                except ValueError:
                    pass
            fo[f] = F.outcome(BY[f], v, d["gold"][f])
        res[d["id"]] = fo
    return res


def monthly_income(rec):
    t = rec.get("doc_type")
    try:
        if t == "pay_stub":
            return round(F.money(rec.get("gross_pay")) * PER_YEAR[rec.get("pay_frequency")] / 12, 2)
        if t == "bank_statement":
            return F.money(rec.get("payroll_total"))
        if t == "hardship_letter":
            return F.money(rec.get("stated_monthly_income")) if rec.get("stated_monthly_income") is not None else None
    except (TypeError, ValueError, KeyError):
        return None
    return None


def decision(rec, d):
    """Illustrative HP-2027-04 income step: recency, payment-to-income band, and for letters the loan and route."""
    if rec is None:
        return ("unreadable",)
    t = rec.get("doc_type")
    try:
        pe = F.to_date(rec.get("period_end"))
    except (ValueError, TypeError):
        pe = None
    up = date.fromisoformat(d["uploaded"])
    if pe is None:
        fresh = "undated"
    else:
        fresh = "fresh" if 0 <= (up - pe).days <= 60 else "stale"
    inc = monthly_income(rec)
    if inc is None or inc <= 0:
        band = "income_needed"
    else:
        pti = d["payment"] / inc
        band = "review" if pti <= 0.20 else ("defer2" if pti <= 0.35 else "modify")
    if t == "hardship_letter":
        route = "disaster" if rec.get("hardship_reason") == "disaster" else "standard"
        return (t, fresh, band, F.ident(rec.get("loan_last4")), route)
    return (t, fresh, band)


def gold_record(d):
    return d["gold"]
