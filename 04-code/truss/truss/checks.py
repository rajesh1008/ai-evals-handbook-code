"""Chapter 9: verifiers, the code checks that run before any judge (Truss 0.12).

A verifier reads one trace and returns one of four outcomes with the evidence
for it: pass, fail, cannot_tell (the inputs it needs are missing or broken) or
not_applicable. Verifiers compose into a suite that runs them in dependency
order: when a check a verifier depends on fails or cannot tell, the dependent
returns cannot_tell instead of guessing. The module also carries the parts a
check is built from (a small schema validator, money and date extraction,
day-count arithmetic, calendar windows) and the parts it is validated with
(precision and recall from reading, mutation testing, boundary cases, overlap).
"""
import calendar
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .rates import wilson

PASS, FAIL, CANNOT, NA = "pass", "fail", "cannot_tell", "not_applicable"
OUTCOMES = (PASS, FAIL, CANNOT, NA)


@dataclass
class Result:
    outcome: str
    evidence: str = ""
    check: str = ""
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError(f"unknown outcome {self.outcome!r}")


@dataclass
class Verifier:
    """One code check. fn(trace, upstream) -> Result. needs: ids of verifiers whose
    failure or cannot_tell makes this one cannot_tell."""
    id: str
    name: str
    fn: object
    modes: tuple = ()
    cards: tuple = ()
    needs: tuple = ()
    version: str = "1.0"
    owner: str = ""
    layer: int = 1
    applies: object = None         # applies(trace) -> bool; False gives not_applicable before anything else

    def __call__(self, trace, upstream=None):
        upstream = upstream or {}
        if self.applies is not None and not self.applies(trace):
            return Result(NA, "does not apply", self.id)
        for n in self.needs:
            u = upstream.get(n)
            if u is not None and u.outcome in (FAIL, CANNOT):
                return Result(CANNOT, f"upstream {n} {u.outcome}", self.id)
        r = self.fn(trace, upstream)
        r.check = self.id
        return r


class Suite:
    def __init__(self, verifiers):
        ids = [v.id for v in verifiers]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate verifier id")
        self.by_id = {v.id: v for v in verifiers}
        self.order = self._order()

    def _order(self):
        done, out = set(), []

        def visit(i, stack=()):
            if i in done:
                return
            if i in stack:
                raise ValueError(f"dependency cycle through {i}")
            for n in self.by_id[i].needs:
                if n not in self.by_id:
                    raise ValueError(f"{i} needs unknown verifier {n}")
                visit(n, stack + (i,))
            done.add(i)
            out.append(i)
        for i in self.by_id:
            visit(i)
        return out

    def run(self, trace):
        res = {}
        for i in self.order:
            res[i] = self.by_id[i](trace, res)
        return res

    def run_all(self, traces):
        t0 = time.perf_counter()
        out = {t["trace_id"]: self.run(t) for t in traces}
        return out, time.perf_counter() - t0


def verdict(results):
    """Trace-level composition: any fail fails; else any cannot_tell is cannot_tell; else pass."""
    o = [r.outcome for r in results.values()]
    if FAIL in o:
        return FAIL
    if CANNOT in o:
        return CANNOT
    return PASS if PASS in o else NA


def tally(all_results, vid):
    c = {k: 0 for k in OUTCOMES}
    for res in all_results.values():
        c[res[vid].outcome] += 1
    return c


def overlap(all_results, ids=None):
    """Co-flag matrix: m[a][b] = traces failed by both a and b (diagonal = failed by a)."""
    ids = ids or next(iter(all_results.values())).keys()
    m = {a: {b: 0 for b in ids} for a in ids}
    for res in all_results.values():
        f = [a for a in ids if res[a].outcome == FAIL]
        for a in f:
            for b in f:
                m[a][b] += 1
    return m


# ---------------------------------------------------------------- schema
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def validate(value, schema, path="$"):
    """A JSON Schema subset: type, required, properties, additionalProperties,
    enum, pattern, minimum, maximum, items, minItems, format=date. Returns errors."""
    errs = []
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        ok = False
        for x in ts:
            if x == "number":
                ok |= isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
            elif x == "integer":
                ok |= isinstance(value, int) and not isinstance(value, bool)
            else:
                ok |= isinstance(value, _TYPES[x])
        if not ok:
            return [f"{path}: expected {t}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errs.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if schema.get("format") == "date":
            try:
                date.fromisoformat(value)
            except ValueError:
                errs.append(f"{path}: {value!r} is not a date")
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: {value} < {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: {value} > {schema['maximum']}")
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errs.append(f"{path}: missing {k}")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected {k}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, v in enumerate(value):
                errs += validate(v, schema["items"], f"{path}[{i}]")
    return errs


# ---------------------------------------------------------------- extraction
MONEY = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)")
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MESES = {m: i for i, m in enumerate(["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                                     "agosto", "septiembre", "octubre", "noviembre", "diciembre"]) if m}
_MN = "|".join(MONTHS)
_DATE_PATTERNS = [
    (re.compile(rf"\b({_MN})\s+(\d{{1,2}}),\s+(\d{{4}})", re.I), lambda m: (int(m[3]), MONTHS[m[1].lower()], int(m[2]))),
    (re.compile(rf"\b(\d{{1,2}})\s+({_MN})\s+(\d{{4}})", re.I), lambda m: (int(m[3]), MONTHS[m[2].lower()], int(m[1]))),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), lambda m: (int(m[3]), int(m[1]), int(m[2]))),
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(r"\b(\d{1,2}) de (" + "|".join(MESES) + r") de (\d{4})", re.I),
     lambda m: (int(m[3]), MESES[m[2].lower()], int(m[1]))),
]


def money(text):
    """Dollar amounts in a text, as Decimals, in order of appearance."""
    return [Decimal(m.group(1).replace(",", "")) for m in MONEY.finditer(text or "")]


def dates(text):
    """Full dates in a text (four formats in English, one in Spanish), in order of appearance."""
    found = []
    for rx, f in _DATE_PATTERNS:
        for m in rx.finditer(text or ""):
            try:
                found.append((m.start(), date(*f(m))))
            except ValueError:
                pass
    return [d for _, d in sorted(found)]


def numbers(text):
    """Every number token in a text (money, plain numbers, percentages) as strings without commas."""
    return [n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")]


# ---------------------------------------------------------------- arithmetic
CONVENTIONS = ("actual/365", "actual/360", "30/360")
CENT = Decimal("0.01")


def cents(x):
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


def days_between(start, end, convention):
    """Interest days from start to end under a day-count convention (30/360 is the US rule)."""
    if convention not in CONVENTIONS:
        raise ValueError(f"unknown day-count convention {convention!r}")
    if convention == "30/360":
        d1, d2 = min(start.day, 30), end.day
        if d2 == 31 and d1 == 30:
            d2 = 30
        return 360 * (end.year - start.year) + 30 * (end.month - start.month) + (d2 - d1)
    return (end - start).days


def basis(convention):
    return 365 if convention == "actual/365" else 360


def per_diem(principal, apr, convention):
    """Daily interest, unrounded: principal x APR / year basis."""
    return Decimal(str(principal)) * Decimal(str(apr)) / basis(convention)


def interest(principal, apr, start, end, convention):
    return cents(per_diem(principal, apr, convention) * days_between(start, end, convention))


def months_before(d, n):
    """The same calendar date n months earlier (clamped to the month's last day)."""
    y, m = divmod(d.year * 12 + d.month - 1 - n, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def within_months(event_end, as_of, months=12, anniversary_inside=True):
    """True when event_end falls in the window of `months` calendar months ending on as_of.
    By default the same calendar date `months` earlier counts as inside (Chapter 9's reading).
    anniversary_inside=False gives "fewer than 12 calendar months" (ops-1.1, Chapter 14; Chapter 15's C-03 v1.1)."""
    start = months_before(as_of, months)
    return (start <= event_end if anniversary_inside else start < event_end) and event_end <= as_of


def to_date(x):
    if isinstance(x, date) and not isinstance(x, datetime):
        return x
    return date.fromisoformat(str(x)[:10])


# ---------------------------------------------------------------- validation
def precision_recall(flags, read, truth):
    """flags: set of trace ids a check failed; read: ids a person read (a sample);
    truth: set of ids that really fail, as far as the people reading know.
    Precision uses every flag (each flag is read); recall uses only the read sample."""
    tp = len(flags & truth)
    p = (tp, len(flags))
    sample_true = read & truth
    r = (len(sample_true & flags), len(sample_true))
    return {"precision": p, "precision_wilson": wilson(*p) if p[1] else (0, 1),
            "recall": r, "recall_wilson": wilson(*r) if r[1] else (0, 1),
            "false_flags": sorted(flags - truth), "missed_in_sample": sorted(sample_true - flags)}


def mutation_score(verifier, traces, mutators, upstream_fn=None):
    """Plant a known failure in passing traces and count how many the verifier kills.
    mutators: {name: f(trace) -> mutated copy or None when it does not apply}."""
    out = {}
    for name, f in mutators.items():
        applied, killed, survivors = 0, 0, []
        for t in traces:
            m = f(t)
            if m is None:
                continue
            applied += 1
            up = upstream_fn(m) if upstream_fn else {}
            if verifier(m, up).outcome == FAIL:
                killed += 1
            else:
                survivors.append(t["trace_id"])
        out[name] = {"applied": applied, "killed": killed, "survivors": survivors}
    return out


def boundary(fn, cases):
    """cases: [(label, args, expected)]; returns rows with the verdict and whether it matched."""
    rows = []
    for label, args, expected in cases:
        got = fn(*args)
        rows.append({"case": label, "expected": expected, "got": got, "ok": got == expected})
    return rows
