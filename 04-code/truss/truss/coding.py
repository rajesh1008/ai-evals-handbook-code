"""Chapter 5: error analysis, from a pile of traces to a first failure taxonomy.

Module version 0.8.0 (the slot between Chapter 4's `layers` and Chapter 6's `taxonomy`).
Plain Python, no dependencies beyond the standard library:

- `OpenCode`: one row per trace read, holding the one-sentence note written before any category.
- `note_problems`: the lint a note must pass (one sentence, concrete, not a category name).
- `Index`: a vector index over notes for searching by meaning. The default vectoriser is a
  lexical stand-in (word and character n-gram TF-IDF); pass `embed=` to use an embedding model.
- `suggest_groups`: single-link grouping of notes above a similarity threshold, as a starting
  point for axial coding (a person decides; the suggestion only orders the pile).
- `Category` and `axial`: categories built from open codes by explicit, reasoned decisions.
- `saturation_curve`, `last_new`, `detect_prob`, `detectable_rate`: when to stop reading, and what
  a reading of n traces could not have seen.
- `cohen_kappa` and `confusion`: agreement between two annotators, and where they part.
- `first_wrong_step`: the earliest span in a trajectory that a failure's origin rule points at.
- `Hypothesis`: a category's suspected cause with the test that would confirm or reject it.
- `codebook_markdown`: the taxonomy table a release prints.
"""
import math
import re
from collections import Counter, OrderedDict, defaultdict
from dataclasses import dataclass, field

MODULE_VERSION = "0.8.0"

# Words that name a category or a feeling rather than what happened in the trace.
VAGUE = {"wrong", "bad", "incorrect", "error", "hallucination", "hallucinated", "issue", "problem",
         "poor", "unhelpful", "confusing", "weird", "off", "fail", "failed", "failure"}


@dataclass
class OpenCode:
    n: int                      # reading position (1-based)
    trace_id: str
    source: str                 # 'sample', 'first_pass' or 'complaint'
    flow: str
    verdict: str                # pass | fail | cannot_tell
    note: str = ""              # one sentence, in the borrower's terms, written before any category
    step: str = ""              # the first step that went wrong (span kind or name), if known
    annotator: str = ""
    minutes: float = 0.0
    category: str = ""          # filled by axial coding, never during the first reading


def note_problems(note, verdict="fail"):
    """Return the reasons a note would be sent back. An empty list means it passes.
    A failing trace needs a note of 4 to 30 words, one sentence, that says something a second
    reader could check: a number, a date, a tool or document, or a quoted phrase, and more than
    category words."""
    out = []
    if verdict != "fail":
        return out
    words = re.findall(r"[A-Za-z0-9$%'-]+", note)
    if len(words) < 4:
        out.append("too short to check")
    if len(words) > 30:
        out.append("more than one finding")
    if re.search(r"[.!?]\s+[A-Z]", note.strip()):
        out.append("more than one sentence")
    content = [w.lower() for w in words if w.lower() not in VAGUE and len(w) > 2]
    if len(content) < 3:
        out.append("names a category, not what happened")
    concrete = re.search(r"\d|\$|'|\"|tool|schedule|letter|statement|offer|loan|officer|"
                         r"person|date|state|income|deferral|waiv|grace|title|payoff|balance|spanish|per diem|"
                         r"interest|day|month",
                         note, re.I)
    if not concrete:
        out.append("nothing a second reader could check")
    return out


# ---------------------------------------------------------------- searching by meaning

def _features(text, ngram=(3, 5)):
    t = " " + re.sub(r"[^a-z0-9$ ]", " ", text.lower()) + " "
    t = re.sub(r"\s+", " ", t)
    feats = Counter(w for w in t.split() if len(w) > 2)
    for n in range(ngram[0], ngram[1] + 1):
        feats.update(t[i:i + n] for i in range(len(t) - n + 1))
    return feats


class Index:
    """Cosine search over notes. `embed(texts) -> list of vectors` replaces the lexical
    stand-in; everything else stays the same."""

    def __init__(self, texts, ids=None, embed=None):
        self.texts, self.ids = list(texts), list(ids or range(len(texts)))
        self.embed = embed
        if embed:
            self.vecs = [self._norm(dict(enumerate(v))) for v in embed(self.texts)]
        else:
            feats = [_features(t) for t in self.texts]
            df = Counter(f for fs in feats for f in fs)
            n = len(feats)
            self.idf = {f: math.log((1 + n) / (1 + d)) + 1 for f, d in df.items()}
            self.vecs = [self._norm({f: c * self.idf[f] for f, c in fs.items()}) for fs in feats]

    @staticmethod
    def _norm(v):
        s = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {k: x / s for k, x in v.items()}

    def vector(self, text):
        if self.embed:
            return self._norm(dict(enumerate(self.embed([text])[0])))
        fs = _features(text)
        return self._norm({f: c * self.idf.get(f, 0.0) for f, c in fs.items() if f in self.idf})

    @staticmethod
    def cos(a, b):
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(k, 0.0) for k, x in a.items())

    def search(self, query, k=5, exclude=None):
        q = self.vector(query) if isinstance(query, str) else query
        scored = [(self.cos(q, v), i) for i, v in enumerate(self.vecs) if self.ids[i] != exclude]
        scored.sort(key=lambda x: (-x[0], str(self.ids[x[1]])))
        return [(self.ids[i], round(s, 3), self.texts[i]) for s, i in scored[:k]]


def jaccard_search(texts, ids, query, k=5, exclude=None):
    """The word-overlap baseline: Jaccard similarity on word sets."""
    def words(s):
        return {w for w in re.findall(r"[a-z0-9$]+", s.lower()) if len(w) > 2}
    q = words(query)
    scored = []
    for t, i in zip(texts, ids):
        if i == exclude:
            continue
        w = words(t)
        scored.append((len(q & w) / len(q | w) if q | w else 0.0, i, t))
    scored.sort(key=lambda x: (-x[0], str(x[1])))
    return [(i, round(s, 3), t) for s, i, t in scored[:k]]


def precision_at_k(results_by_query, label):
    """results_by_query: {query_id: [result ids]}; label: {id: category}. Mean share of
    returned neighbours that share the query's category."""
    vals = [sum(label[r] == label[q] for r in rs) / len(rs) for q, rs in results_by_query.items() if rs]
    return sum(vals) / len(vals) if vals else 0.0


def suggest_groups(index, threshold=0.35):
    """Single-link groups: notes joined when their cosine similarity is at least threshold.
    Returns lists of ids, largest first. A suggestion for the axial session, never a decision."""
    n = len(index.vecs)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            if index.cos(index.vecs[i], index.vecs[j]) >= threshold:
                parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(index.ids[i])
    return sorted(groups.values(), key=lambda g: (-len(g), str(g[0])))


def purity(groups, label):
    """Share of notes whose group's majority category is their own category."""
    hit = tot = 0
    for g in groups:
        c = Counter(label[i] for i in g)
        hit += c.most_common(1)[0][1]
        tot += len(g)
    return hit / tot if tot else 0.0


# ---------------------------------------------------------------- axial coding

@dataclass
class Category:
    code: str
    name: str
    flows: tuple
    definition: str
    layer: int = 3
    owner: str = ""
    severity: str = "medium"
    members: list = field(default_factory=list)      # trace ids
    memo: str = ""                                    # why these open codes belong together

    def by_source(self, codes):
        src = {c.trace_id: c.source for c in codes}
        return Counter(src[t] for t in self.members)


def axial(codes, assign, categories):
    """Assign every failing open code to a category by an explicit rule.
    `assign(code) -> category code or None`. Returns (categories with members, unassigned).
    A failing code that no rule assigns is returned, never forced into the nearest category."""
    cats = OrderedDict((c.code, c) for c in categories)
    for c in cats.values():
        c.members = []
    left = []
    for oc in codes:
        if oc.verdict != "fail":
            continue
        k = assign(oc)
        if k is None:
            left.append(oc)
            continue
        cats[k].members.append(oc.trace_id)
        oc.category = k
    return list(cats.values()), left


# ---------------------------------------------------------------- saturation

def saturation_curve(codes):
    """[(traces read, failures so far, distinct categories so far)] in reading order."""
    seen, fails, out = OrderedDict(), 0, []
    for oc in sorted(codes, key=lambda c: c.n):
        if oc.verdict == "fail" and oc.category:
            fails += 1
            seen.setdefault(oc.category, oc.n)
        out.append((oc.n, fails, len(seen)))
    return out


def last_new(curve):
    """Reading position at which the last new category appeared (0 if none)."""
    last, prev = 0, 0
    for n, _, k in curve:
        if k > prev:
            last, prev = n, k
    return last


def detect_prob(rate, n):
    """Chance that a mode occurring at `rate` appears at least once in n traces read."""
    return 1 - (1 - rate) ** n


def detectable_rate(n, conf=0.95):
    """Smallest rate a mode needs to appear at least once in n traces with probability conf."""
    return 1 - (1 - conf) ** (1 / n)


# ---------------------------------------------------------------- agreement

def cohen_kappa(a, b):
    """Cohen's kappa for two equal-length label lists."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def confusion(a, b):
    """{(label_a, label_b): count} for the pairs where the annotators differ."""
    return Counter((x, y) for x, y in zip(a, b) if x != y)


# ---------------------------------------------------------------- trajectories

def first_wrong_step(spans, rule):
    """spans: ordered list of dicts with 'kind', 'name', 'seq'. rule: a predicate over
    (index, span, spans) that is true at the step the failure starts. Returns
    (index, span) of the first step the rule accepts, or (None, None)."""
    for i, s in enumerate(spans):
        if rule(i, s, spans):
            return i, s
    return None, None


# ---------------------------------------------------------------- hypotheses

@dataclass
class Hypothesis:
    code: str
    claim: str                 # the suspected cause, stated so it could be wrong
    test: str                  # what would be counted, where, and what result would reject it
    owner: str
    result: str = "not run"    # confirmed | not supported | needs later data | not run
    evidence: str = ""


def codebook_markdown(categories, codes, version="0.1"):
    rows = [f"# Compass failure taxonomy v{version}", "",
            "| Code | Name | Flows | Layer | Owner | Severity | Sample | First pass | Complaints |",
            "|---|---|---|---|---|---|---|---|---|"]
    for c in categories:
        s = c.by_source(codes)
        rows.append(f"| {c.code} | {c.name} | {', '.join(c.flows)} | L{c.layer} | {c.owner} | {c.severity} | "
                    f"{s.get('sample', 0)} | {s.get('first_pass', 0)} | {s.get('complaint', 0)} |")
    rows += ["", "Definitions:", ""] + [f"- **{c.code}** {c.definition}" for c in categories]
    return "\n".join(rows) + "\n"
