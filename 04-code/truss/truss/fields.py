"""Truss 0.14 (Chapter 11): the field scorer.

Scores anything a system pulls out of a document or returns as a schema, one field at a time.
Layer one (schema): parse, known keys, types, enums, required-field coverage per document type.
Layer two (values): normalise by kind (money, date, name, id, enum), then compare exactly or within
a tolerance declared on the field, and record one of five outcomes per field:
  tp (right value), wrong (a value, not the right one), miss (null where a value exists),
  invented (a value where the document has none), tn (null, rightly).
Per field: precision = tp / (tp + wrong + invented), recall = tp / (tp + wrong + miss).
Plus: row matching for tables, document and decision roll-ups, confidence calibration, and an
identity test that every normaliser must pass before any score is trusted.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

OUTCOMES = ("tp", "wrong", "miss", "invented", "tn")
MES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
       "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
LEGAL = {"llc", "inc", "co", "corp", "ltd", "company", "the"}


@dataclass
class FieldSpec:
    name: str
    kind: str                         # money | date | name | id | enum | text
    required: frozenset = frozenset() # document types on which the field must be present
    critical: bool = False            # feeds a decision
    tolerance: float = 0.0            # money: dollars; date: days
    allowed: tuple = ()               # enum values
    match: str = "exact"              # exact | prefix (name tokens may be truncated prefixes)


def money(x):
    """Format only: '$1,234.56', '1234.5', 1234.56 -> 1234.56. Never repairs OCR letters."""
    if x is None:
        return None
    if isinstance(x, bool):
        raise ValueError("bool is not money")
    if isinstance(x, (int, float)):
        return round(float(x), 2)
    s = str(x).strip().replace("$", "").replace(",", "").replace(" ", "")
    if not re.fullmatch(r"-?\d+(\.\d+)?", s):
        raise ValueError(f"not money: {x!r}")
    return round(float(s), 2)


def to_date(x):
    if x is None:
        return None
    if isinstance(x, date):
        return x
    s = str(x).strip().lower().replace(",", "")
    for f in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    m = re.fullmatch(r"(\d{1,2}) de ([a-z]+) de (\d{4})", s)
    if m and m.group(2) in MES:
        return date(int(m.group(3)), MES[m.group(2)], int(m.group(1)))
    m = re.fullmatch(r"([a-z]+)\.? (\d{1,2}) (\d{4})", s)
    if m and m.group(1)[:3] in MON:
        return date(int(m.group(3)), MON[m.group(1)[:3]], int(m.group(2)))
    raise ValueError(f"not a date: {x!r}")


def name(x):
    if x is None:
        return None
    s = unicodedata.normalize("NFKD", str(x))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(w for w in s.split() if w not in LEGAL)


def ident(x):
    return None if x is None else re.sub(r"\D", "", str(x))


def normalise(spec: FieldSpec, x):
    if x is None:
        return None
    return {"money": money, "date": to_date, "name": name, "id": ident,
            "enum": lambda v: str(v).strip().lower(), "text": lambda v: " ".join(str(v).split())}[spec.kind](x)


def same(spec: FieldSpec, got, gold) -> bool:
    if spec.kind == "money":
        return abs(got - gold) <= spec.tolerance + 1e-9
    if spec.kind == "date":
        return abs((got - gold).days) <= spec.tolerance
    if spec.kind == "name" and spec.match == "prefix":
        g, t = got.split(), gold.split()
        return bool(g) and len(g) <= len(t) and all(t[i].startswith(w) for i, w in enumerate(g)) and \
            (len(g) == len(t) or len(g[-1]) >= 1)
    return got == gold


def outcome(spec: FieldSpec, got, gold) -> str:
    """One of OUTCOMES. A value that fails to normalise counts as wrong (or invented)."""
    if gold is None:
        return "tn" if got is None else "invented"
    if got is None:
        return "miss"
    try:
        g = normalise(spec, got)
    except (ValueError, TypeError):
        return "wrong"
    return "tp" if same(spec, g, normalise(spec, gold)) else "wrong"


def layer_one(obj, specs, doc_type_key="doc_type", extra_keys=("payroll_deposits", "confidence")):
    """Schema validity, type correctness and required-field coverage for one extraction."""
    if obj is None:
        return {"parsed": False, "unknown": [], "absent": [], "type_errors": [], "enum_errors": [], "required_missing": []}
    names = {s.name for s in specs}
    unknown = sorted(k for k in obj if k not in names and k not in extra_keys)
    absent = sorted(n for n in names if n not in obj)
    type_errors, enum_errors, req = [], [], []
    dt = obj.get(doc_type_key)
    for s in specs:
        v = obj.get(s.name)
        if v is None:
            if dt in s.required:
                req.append(s.name)
            continue
        if s.kind == "enum" and str(v).strip().lower() not in s.allowed:
            enum_errors.append(s.name)
            continue
        try:
            normalise(s, v)
        except (ValueError, TypeError):
            type_errors.append(s.name)
    return {"parsed": True, "unknown": unknown, "absent": absent, "type_errors": type_errors,
            "enum_errors": enum_errors, "required_missing": req}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def upper_one_sided(k, n):
    """One-sided 95% upper bound (Wilson with z = 1.645) on an error rate."""
    return wilson(k, n, 1.645)[1]


def field_table(rows):
    """rows: iterable of (field, outcome). Returns per-field counts, precision, recall, accuracy."""
    t = {}
    for f, o in rows:
        t.setdefault(f, {k: 0 for k in OUTCOMES})[o] += 1
    out = {}
    for f, c in t.items():
        pp = c["tp"] + c["wrong"] + c["invented"]
        ap = c["tp"] + c["wrong"] + c["miss"]
        n = sum(c.values())
        out[f] = {**c, "n": n, "precision": c["tp"] / pp if pp else float("nan"),
                  "recall": c["tp"] / ap if ap else float("nan"), "accuracy": (c["tp"] + c["tn"]) / n if n else float("nan"),
                  "errors_where_present": c["wrong"] + c["miss"], "present": ap}
    return out


def doc_rollup(outcomes_by_doc, fields=None):
    """outcomes_by_doc: {doc: {field: outcome}}. Share of fields right and all-right per document."""
    res = {}
    for d, fo in outcomes_by_doc.items():
        fo = {k: v for k, v in fo.items() if fields is None or k in fields}
        ok = sum(v in ("tp", "tn") for v in fo.values())
        res[d] = {"share": ok / len(fo) if fo else float("nan"), "all": ok == len(fo)}
    return res


def match_rows(pred, gold, amount_tol=0.0, date_tol=0):
    """Greedy one-to-one row matching on date and amount. Returns tp, extra, missed, duplicates."""
    pred = list(pred or []); gold = list(gold or [])
    used = [False] * len(gold); tp = 0; extra = []; dup = 0
    seen = set()
    for r in pred:
        try:
            d, a = to_date(r.get("date")), money(r.get("amount"))
        except (ValueError, TypeError, AttributeError):
            extra.append(r); continue
        key = (d, a)
        hit = None
        for j, g in enumerate(gold):
            if not used[j] and abs((to_date(g["date"]) - d).days) <= date_tol and abs(money(g["amount"]) - a) <= amount_tol + 1e-9:
                hit = j; break
        if hit is None:
            dup += key in seen
            extra.append(r)
        else:
            used[hit] = True; tp += 1
        seen.add(key)
    return {"tp": tp, "extra": len(extra), "missed": used.count(False), "duplicates": dup}


def calibration(conf, correct, edges=(0.0, 0.5, 0.8, 0.9, 0.95, 0.99, 1.0001)):
    """Reliability table and expected calibration error (ECE) for stated confidences."""
    rows, ece, n = [], 0.0, len(conf)
    for lo, hi in zip(edges, edges[1:]):
        idx = [i for i, c in enumerate(conf) if lo <= c < hi]
        if not idx:
            continue
        mc = sum(conf[i] for i in idx) / len(idx)
        acc = sum(correct[i] for i in idx) / len(idx)
        rows.append({"bin": f"{lo:.2f}-{min(hi, 1):.2f}", "n": len(idx), "mean_conf": mc, "accuracy": acc})
        ece += len(idx) / n * abs(mc - acc)
    return rows, ece


def identity_test(normaliser, cases):
    """A normaliser must return every gold value unchanged from its own printed forms.
    cases: [(printed_text, gold_value)]. Returns the failures."""
    bad = []
    for text, gold in cases:
        try:
            got = normaliser(text)
        except (ValueError, TypeError) as e:
            bad.append((text, gold, repr(e))); continue
        if got != gold:
            bad.append((text, gold, got))
    return bad


def parse_json(raw):
    """Strict parse first; then one declared repair (strip a Markdown fence). Returns (obj, repaired)."""
    try:
        o = json.loads(raw)
        return (o if isinstance(o, dict) else None), False
    except (json.JSONDecodeError, TypeError):
        pass
    t = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw or "")
    try:
        o = json.loads(t)
        return (o if isinstance(o, dict) else None), True
    except json.JSONDecodeError:
        return None, False


def implausible_dates(obj, received, keys=("period_end",)):
    """Plausibility check that needs no gold: a document cannot describe a date after the day it was
    received. Returns the names of the fields that fail. Unparseable dates are left to layer_one."""
    rec = to_date(received)
    bad = []
    for k in keys:
        try:
            v = to_date((obj or {}).get(k))
        except (ValueError, TypeError):
            continue
        if v is not None and v > rec:
            bad.append(k)
    return bad
