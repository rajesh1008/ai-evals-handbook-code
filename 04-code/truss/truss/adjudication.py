"""Truss 0.16 (Chapter 13): adjudication records for an expert-labelled gold set.

Two experts label the same traces blind; disagreements, and agreements an audit contests, go to an
adjudicator who records a ruling with a kind, a reason and the guideline and policy versions in force.
A gold label exists only as the output of a record. The book calls this release Truss v2.5.

Kinds of ruling:
  agreed     both blind labels match and no audit contests them
  slip       one reader misread the trace; the trace and the guideline settle it
  fact       the trace is ambiguous on a fact; if it cannot be settled the gold is cannot_tell
  guideline  a guideline sentence was read two ways; the sentence is rewritten and every trace it
             touches is re-read under the next revision
  policy     the written policy is silent or contradicts practice; the policy owner rules, and the
             gold stays pending until the ruling has an identifier
"""
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field

KINDS = ("agreed", "slip", "fact", "guideline", "policy")
CANNOT_TELL = "cannot_tell"


@dataclass(frozen=True)
class Label:
    """One expert's blind label on one trace."""
    trace_id: str
    annotator: str
    label: str
    guideline: str
    minutes: float = 0.0
    sitting: str = ""
    minute_in_sitting: float = 0.0
    labelled_on: str = ""
    reason: str = ""
    policy_question: bool = False


@dataclass
class Record:
    """The adjudication record that makes a gold label."""
    trace_id: str
    labels: tuple  # ((anonymised reader, label), ...): the adjudicator never sees names
    gold: object
    kind: str
    adjudicator: str
    rationale: str
    guideline: str
    policy: str
    decided_on: str
    status: str = "final"  # final, pending, cannot_tell
    escalated_to: str = ""
    ruling_id: str = ""
    audit: str = ""
    history: list = field(default_factory=list)

    def digest(self):
        body = {k: v for k, v in asdict(self).items() if k != "history"}
        return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]


def pairs(a, b):
    """Match two readers' labels by trace: [(trace_id, Label a, Label b)] for traces both labelled."""
    bi = {x.trace_id: x for x in b}
    return [(x.trace_id, x, bi[x.trace_id]) for x in a if x.trace_id in bi]


def adjudicate(trace_id, a, b, ruling=None, *, adjudicator, guideline, policy, decided_on, audit=""):
    """The adjudication rule as code. a, b: the two blind labels. ruling: None when they agree and
    no audit contests them, otherwise {gold, kind, rationale[, escalated_to, ruling_id]}."""
    labels = (("A", a.label), ("B", b.label))
    if a.label == b.label and ruling is None:
        if audit:
            raise ValueError(f"{trace_id}: an audit contests the agreed label; it needs a ruling")
        return Record(trace_id, labels, a.label, "agreed", adjudicator, "blind labels agree", guideline,
                      policy, decided_on)
    if ruling is None:
        raise ValueError(f"{trace_id}: readers disagree ({a.label} / {b.label}); a ruling is required")
    kind, why = ruling.get("kind"), ruling.get("rationale", "").strip()
    if kind not in KINDS[1:] or not why:
        raise ValueError(f"{trace_id}: a ruling needs a kind in {KINDS[1:]} and a written rationale")
    gold, status = ruling.get("gold"), "final"
    if kind == "policy":
        if not ruling.get("escalated_to"):
            raise ValueError(f"{trace_id}: a policy ruling must be escalated to the policy owner")
        if not ruling.get("ruling_id"):
            gold, status = None, "pending"
    if gold == CANNOT_TELL:
        status = CANNOT_TELL
    return Record(trace_id, labels, gold, kind, adjudicator, why, guideline, policy, decided_on, status,
                  ruling.get("escalated_to", ""), ruling.get("ruling_id", ""), audit)


def rederive(record, new_gold, *, policy, ruling_id, decided_on, why):
    """A policy change re-derives a gold label from its record without re-reading; the old value is kept."""
    record.history.append({"gold": record.gold, "policy": record.policy, "decided_on": record.decided_on,
                           "digest": record.digest()})
    record.gold, record.policy, record.ruling_id, record.decided_on = new_gold, policy, ruling_id, decided_on
    record.rationale = f"{record.rationale}; re-derived: {why}"
    record.status = "final"
    return record


def gold(records):
    """{trace_id: label} for final records. Refuses a pending record; drops cannot_tell from the set."""
    pend = [r.trace_id for r in records if r.status == "pending"]
    if pend:
        raise ValueError(f"{len(pend)} records wait for a policy ruling, e.g. {pend[:3]}")
    return {r.trace_id: r.gold for r in records if r.status == "final"}


def manifest(records, name, version):
    """Counts by kind and status and a digest over every record digest."""
    d = hashlib.sha256("".join(sorted(r.digest() for r in records)).encode()).hexdigest()[:12]
    return {"name": name, "version": version, "n": len(records), "digest": d,
            "kinds": dict(Counter(r.kind for r in records)), "status": dict(Counter(r.status for r in records))}


# ---------------------------------------------------------------- agreement on the same labels

def percent_agreement(a, b):
    return sum(x == y for x, y in zip(a, b)) / len(a) if a else float("nan")


def kappa(a, b):
    """Cohen's kappa for two readers."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = percent_agreement(a, b)
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def alpha(units):
    """Krippendorff's alpha, nominal, for units = [[value, value, ...], ...]; None marks a missing
    value and units with fewer than two values are ignored."""
    o = defaultdict(float)
    for u in units:
        vals = [v for v in u if v is not None]
        m = len(vals)
        if m < 2:
            continue
        for i, x in enumerate(vals):
            for j, y in enumerate(vals):
                if i != j:
                    o[(x, y)] += 1 / (m - 1)
    n_c = defaultdict(float)
    for (x, _), w in o.items():
        n_c[x] += w
    n = sum(n_c.values())
    if n <= 1:
        return float("nan")
    d_o = sum(w for (x, y), w in o.items() if x != y)
    d_e = sum(n_c[x] * n_c[y] for x in n_c for y in n_c if x != y) / (n - 1)
    return 1.0 if d_e == 0 else 1 - d_o / d_e


def matrix(a, b, labels):
    """Agreement matrix: rows reader a, columns reader b."""
    m = [[0] * len(labels) for _ in labels]
    ix = {k: i for i, k in enumerate(labels)}
    for x, y in zip(a, b):
        m[ix[x]][ix[y]] += 1
    return m


def per_label_kappa(a, b, labels):
    """One-against-the-rest kappa for each label: where in the label set the disagreement sits."""
    return {k: kappa([x == k for x in a], [y == k for y in b]) for k in labels}


def bootstrap_kappa(a, b, reps=2000, seed=2026):
    """Percentile 95% interval for kappa by resampling traces."""
    import random
    g, n, ks = random.Random(seed), len(a), []
    for _ in range(reps):
        ix = [g.randrange(n) for _ in range(n)]
        ks.append(kappa([a[i] for i in ix], [b[i] for i in ix]))
    ks.sort()
    return ks[int(0.025 * reps)], ks[int(0.975 * reps) - 1]


# ---------------------------------------------------------------- expert time and drift

def expert_hours(labels, other=(), rate=60.0):
    """labels: Label records; other: [(person, activity, minutes)]. Hours and dollars by person."""
    h = Counter()
    for x in labels:
        h[x.annotator] += x.minutes / 60
    for person, _, minutes in other:
        h[person] += minutes / 60
    return {"by_person": dict(h), "hours": sum(h.values()), "dollars": sum(h.values()) * rate}


def by_minute(pairs_, edges=(0, 15, 30, 45, 60, 1e9)):
    """Disagreement rate by how far into the sitting the later of the two labels fell."""
    out = []
    for lo, hi in zip(edges, edges[1:]):
        sel = [(a, b) for _, a, b in pairs_ if lo <= max(a.minute_in_sitting, b.minute_in_sitting) < hi]
        out.append({"from": lo, "to": hi, "n": len(sel), "disagree": sum(a.label != b.label for a, b in sel)})
    return out


def anchor_agreement(gold_map, labels, period=lambda x: x.labelled_on):
    """Each reader's agreement with adjudicated gold on re-read anchor traces, by period."""
    t = defaultdict(lambda: [0, 0])
    for x in labels:
        if x.trace_id in gold_map:
            k = (x.annotator, period(x))
            t[k][0] += x.label == gold_map[x.trace_id]
            t[k][1] += 1
    return {k: {"agree": v[0], "n": v[1], "rate": v[0] / v[1]} for k, v in sorted(t.items())}
