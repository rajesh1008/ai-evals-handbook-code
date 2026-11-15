"""Truss 0.17 (Chapter 14): annotation as an operation.

Assignment with overlap and hidden anchors, agreement across more than two readers (pairwise Cohen's
kappa and Fleiss' kappa), the reader-against-anchor table, final labels from readings and
adjudications, the agreed-label audit draw, selection of which traces people read (random,
uncertainty-driven, failure-driven, mixed) with inclusion probabilities and the Horvitz-Thompson rate,
cost per final label, the annotation-debt register and the alignment-session record that turns a
disagreement cell into a guideline change.
"""
import hashlib
import random
from collections import Counter, defaultdict
from itertools import combinations

from .adjudication import kappa, matrix  # Cohen's kappa and the agreement matrix (Chapter 13)

DEBT_KINDS = ("unread", "unadjudicated", "re-read after guideline change", "cannot tell open",
              "authored awaiting review", "audit due")


# ---------------------------------------------------------------- assignment
def assign(trace_ids, readers, triple=0.2, anchors=(), seed=2026, must_include=None):
    """Every trace to two readers (pairs rotate so each pair gets a third), a share `triple` to all
    three, every anchor to everyone. `must_include(trace_id)` may name a reader who must be on the
    trace (for example the bilingual reader on Spanish traces). Order is shuffled so anchors sit
    among live traces. Returns a list of (position, trace_id, reader)."""
    g = random.Random(seed)
    pairs = list(combinations(readers, 2))
    ids = list(trace_ids)
    n_triple = round(triple * len(ids))
    triple_ids = set(g.sample(ids, n_triple))
    jobs = []
    for i, t in enumerate(ids):
        if t in triple_ids:
            who = list(readers)
        else:
            who = list(pairs[i % len(pairs)])
            need = must_include(t) if must_include else None
            if need and need not in who:
                who = [need, next(r for r in who if r != need)]
        jobs += [(t, r) for r in who]
    jobs += [(a, r) for a in anchors for r in readers]
    g.shuffle(jobs)
    return [(k, t, r) for k, (t, r) in enumerate(jobs)]


def load_by_reader(jobs):
    return Counter(r for _, _, r in jobs)


# ---------------------------------------------------------------- agreement
def pairwise(readings, readers):
    """readings: {trace_id: {reader: label}}. Cohen's kappa for each pair on the traces both read."""
    out = {}
    for a, b in combinations(readers, 2):
        both = [t for t, r in readings.items() if a in r and b in r]
        la, lb = [readings[t][a] for t in both], [readings[t][b] for t in both]
        out[(a, b)] = {"n": len(both), "agree": sum(x == y for x, y in zip(la, lb)),
                       "kappa": kappa(la, lb) if both else float("nan")}
    return out


def fleiss_kappa(units, labels):
    """Fleiss' kappa for units each read by the same number of readers: units = [[label, ...], ...]."""
    units = [u for u in units if u]
    m = len(units[0])
    assert all(len(u) == m for u in units), "Fleiss' kappa needs the same number of readers per unit"
    n = len(units)
    counts = [Counter(u) for u in units]
    p_j = {k: sum(c[k] for c in counts) / (n * m) for k in labels}
    p_i = [(sum(v * v for v in c.values()) - m) / (m * (m - 1)) for c in counts]
    p_bar, p_e = sum(p_i) / n, sum(v * v for v in p_j.values())
    return 1.0 if p_e == 1 else (p_bar - p_e) / (1 - p_e)


def pair_matrix(readings, a, b, labels):
    both = [t for t, r in readings.items() if a in r and b in r]
    return matrix([readings[t][a] for t in both], [readings[t][b] for t in both], labels)


def top_cells(m, labels, k=3):
    cells = [(m[i][j] + m[j][i], labels[i], labels[j]) for i in range(len(labels)) for j in range(i + 1, len(labels))]
    return [(x, y, n) for n, x, y in sorted(cells, reverse=True)[:k] if n]


def anchor_table(readings, gold, readers):
    """Each reader's accuracy on hidden anchors, overall and by gold label."""
    out = {}
    for r in readers:
        rows = [(gold[t], readings[t][r]) for t in gold if r in readings.get(t, {})]
        by = defaultdict(lambda: [0, 0])
        for g_, l_ in rows:
            by[g_][1] += 1
            by[g_][0] += g_ == l_
        out[r] = {"right": sum(g_ == l_ for g_, l_ in rows), "n": len(rows), "by_label": dict(by)}
    return out


# ---------------------------------------------------------------- final labels
def final_labels(readings, adjudicated):
    """Agreed readings stand; any disagreement needs a ruling. Returns ({trace: label}, [pending])."""
    out, pending = {}, []
    for t, r in readings.items():
        vals = set(r.values())
        if len(vals) == 1:
            out[t] = vals.pop()
        elif t in adjudicated:
            out[t] = adjudicated[t]
        else:
            pending.append(t)
    return out, pending


def audit_draw(agreed_ids, share=0.1, seed=2026):
    """The agreed-label audit: a fixed share of agreed traces re-read by the adjudicator."""
    ids = sorted(agreed_ids)
    return sorted(random.Random(seed).sample(ids, max(1, round(share * len(ids))))) if ids else []


# ---------------------------------------------------------------- choosing what people read
def select(frame, k, strategy, score=None, seed=2026, mix_targeted=0, pool=None):
    """Choose k trace IDs from frame. strategy: random | uncertainty | failure | mixed.
    score(trace_id) -> higher means read first (uncertainty or suspected failure). Returns
    (ids, inclusion) where inclusion[trace_id] is the probability the design gave that trace, so a
    rate can be estimated without bias only where every inclusion probability is known and positive.
    With `pool` (for example the traces a pre-labeller disagrees with Compass on), targeted picks are drawn
    at random inside the pool rather than taken from the top of a ranking, so a mixed design keeps exact
    inclusion probabilities: targeted picks first, then the random picks from everything left."""
    ids = sorted(frame)
    g = random.Random(seed)
    if strategy == "random":
        pick = g.sample(ids, k)
        return sorted(pick), {t: k / len(ids) for t in pick}
    if pool is not None:
        pool = sorted(set(pool) & set(ids))
        if strategy == "failure":
            pick = g.sample(pool, min(k, len(pool)))
            return sorted(pick), {t: None for t in pick}   # traces outside the pool had no chance
        if strategy == "mixed":
            top = g.sample(pool, mix_targeted)
            rest = [t for t in ids if t not in set(top)]
            rnd = g.sample(rest, k - mix_targeted)
            p_rest = (k - mix_targeted) / len(rest)
            p_pool = mix_targeted / len(pool) + (1 - mix_targeted / len(pool)) * p_rest
            pset = set(pool)
            return sorted(top + rnd), {t: (p_pool if t in pset else p_rest) for t in top + rnd}
    ranked = sorted(ids, key=lambda t: (-score(t), t))
    if strategy in ("uncertainty", "failure"):
        pick = ranked[:k]
        return sorted(pick), {t: None for t in pick}  # inclusion unknown: no rate from these
    if strategy == "mixed":
        top = ranked[:mix_targeted]
        rest = [t for t in ids if t not in set(top)]
        rnd = g.sample(rest, k - mix_targeted)
        inc = {t: 1.0 for t in top}
        inc.update({t: (k - mix_targeted) / len(rest) for t in rnd})
        return sorted(top + rnd), inc
    raise ValueError(strategy)


def ht_rate(failed, inclusion, n_frame):
    """Horvitz-Thompson estimate of the failure rate in the frame. Refuses unknown inclusion."""
    if any(p is None or p <= 0 for p in inclusion.values()):
        raise ValueError("inclusion probability unknown: a targeted draw cannot give a rate")
    return sum(failed[t] / p for t, p in inclusion.items()) / n_frame


# ---------------------------------------------------------------- cost and debt
def cost_per_label(minutes_by_reader, rates, n_final, extra=()):
    """minutes_by_reader: {reader: total minutes}; rates: {reader: dollars an hour};
    extra: [(what, dollars)] such as adjudication, anchors and sessions. Dollars per final label."""
    parts = [(f"reading ({r})", m / 60 * rates[r]) for r, m in minutes_by_reader.items()] + list(extra)
    total = sum(v for _, v in parts)
    return {"parts": parts, "total": total, "per_label": total / n_final if n_final else float("nan")}


def debt(register):
    """register: [{kind, items, minutes_each, blocks}]; returns hours by kind, total hours and the
    items blocking a rate (a reading that cannot be counted until the debt is paid)."""
    for row in register:
        assert row["kind"] in DEBT_KINDS, row["kind"]
    hours = defaultdict(float)
    for row in register:
        hours[row["kind"]] += row["items"] * row["minutes_each"] / 60
    return {"hours": dict(hours), "total_hours": sum(hours.values()),
            "blocking_items": sum(r["items"] for r in register if r.get("blocks"))}


# ---------------------------------------------------------------- alignment sessions
def session_record(date, cell, count, finding, change=None, sentence=None):
    """One alignment-session item. finding: guideline silent | guideline ambiguous | policy question |
    slip pattern. A guideline finding must name a change to a sentence; nothing is addressed to a
    reader."""
    assert finding in ("guideline silent", "guideline ambiguous", "policy question", "slip pattern")
    if finding.startswith("guideline"):
        assert change and sentence, "a guideline finding names the sentence and the change"
    rec = {"date": date, "cell": cell, "count": count, "finding": finding, "sentence": sentence, "change": change}
    rec["id"] = hashlib.sha256(repr(sorted(rec.items())).encode()).hexdigest()[:12]
    return rec
