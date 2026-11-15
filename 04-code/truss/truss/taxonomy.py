"""Chapter 6: the Living Taxonomy, a versioned list of failure modes.

A taxonomy is data with a version. Every label records the version it was coded
under; every change is one of four operations (add, split, merge, retire); a code
never changes meaning, so a split or merge closes old codes and opens new ones and
the crosswalk says where each old code went. Versions follow three rules:
  patch (0.2.1)  wording only; no label may change
  minor (0.3)    any add, split, merge or retire
  1.0            the owner of the list signs it as a controlled list
Plain Python, no dependencies.
"""
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field

STATUSES = ("active", "provisional", "retired", "closed")
SEVERITIES = ("critical", "high", "medium", "low")


@dataclass
class Mode:
    code: str
    name: str
    flows: tuple
    definition: str
    test: str = ""               # inclusion test: a yes/no question about the trace
    excludes: str = ""           # what looks similar but belongs elsewhere
    layer: int = 0               # lowest layer that can see it (Chapter 4); 0 = not yet placed
    owner: str = ""
    severity: str = "medium"
    status: str = "active"
    added_in: str = "0.1"
    source: str = "error analysis"
    replaced_by: tuple = ()      # codes that took over when this one closed
    guard: str = ""              # for retired modes: the blocking check that stops recurrence
    facets: tuple = ()           # sub-distinctions kept after a merge

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"{self.code}: status {self.status!r}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"{self.code}: severity {self.severity!r}")
        self.flows, self.replaced_by, self.facets = tuple(self.flows), tuple(self.replaced_by), tuple(self.facets)


@dataclass
class Taxonomy:
    version: str
    modes: dict = field(default_factory=dict)
    log: list = field(default_factory=list)

    # ---- reading
    def active(self, flow=None, include_provisional=True):
        ok = ("active", "provisional") if include_provisional else ("active",)
        return [m for m in self.modes.values() if m.status in ok and (flow is None or flow in m.flows)]

    def by_name(self, name):
        hits = [m for m in self.modes.values() if m.name == name]
        if len(hits) != 1:
            raise KeyError(name)
        return hits[0]

    def digest(self):
        """Content hash over codes, names, tests and statuses: two lists with the same digest code the same."""
        body = json.dumps([[m.code, m.name, m.test, m.status, list(m.flows)] for m in
                           sorted(self.modes.values(), key=lambda m: m.code)])
        return hashlib.sha256(body.encode()).hexdigest()[:12]

    # ---- the four operations (each returns self, logs, and requires a reason)
    def _next(self, bump):
        major, minor, *patch = (int(x) for x in self.version.split("."))
        return f"{major}.{minor + 1}" if bump == "minor" else f"{major}.{minor}.{(patch or [0])[0] + 1}"

    def _note(self, op, codes, reason):
        if not reason:
            raise ValueError(f"{op} needs a reason")
        self.log.append({"op": op, "codes": list(codes), "reason": reason})

    def add(self, mode, reason):
        if mode.code in self.modes:
            raise ValueError(f"code {mode.code} already used; codes are never reused")
        self.modes[mode.code] = mode
        self._note("add", [mode.code], reason)
        return self

    def split(self, code, children, reason):
        parent = self._open(code)
        for c in children:
            self.add(c, f"split from {code}")
            self.log.pop()
        parent.status, parent.replaced_by = "closed", tuple(c.code for c in children)
        self._note("split", [code] + [c.code for c in children], reason)
        return self

    def merge(self, codes, into, reason):
        for c in codes:
            self._open(c)
        self.add(into, "merge")
        self.log.pop()
        for c in codes:
            self.modes[c].status, self.modes[c].replaced_by = "closed", (into.code,)
        self._note("merge", list(codes) + [into.code], reason)
        return self

    def retire(self, code, guard, reason):
        m = self._open(code)
        if not guard:
            raise ValueError(f"{code}: retire needs a guard, the blocking check that stops it recurring")
        m.status, m.guard = "retired", guard
        self._note("retire", [code], reason)
        return self

    def reword(self, code, reason, **fields):
        """Patch-level change: wording, tests, owner, layer. Never status, flows or code."""
        m = self.modes[code]
        bad = set(fields) - {"name", "definition", "test", "excludes", "owner", "layer", "severity", "facets"}
        if bad:
            raise ValueError(f"reword cannot change {sorted(bad)}")
        for k, v in fields.items():
            setattr(m, k, tuple(v) if k == "facets" else v)
        self._note("reword", [code], reason)
        return self

    def promote(self, code, reason):
        m = self.modes[code]
        if m.status != "provisional":
            raise ValueError(f"{code} is {m.status}")
        m.status = "active"
        self._note("promote", [code], reason)
        return self

    def _open(self, code):
        m = self.modes[code]
        if m.status in ("closed", "retired"):
            raise ValueError(f"{code} is already {m.status}")
        return m

    def release(self, bump="minor"):
        """Close the change set: bump the version and return the release record."""
        if bump == "patch" and any(e["op"] != "reword" for e in self.log):
            raise ValueError("a patch release may only reword; membership changed")
        rec = {"from": self.version, "to": self._next(bump), "changes": list(self.log)}
        self.version, self.log = rec["to"], []
        rec["digest"] = self.digest()
        return rec

    def crosswalk(self):
        """Old code -> list of current codes a label under it may now belong to (resolved transitively)."""
        out = {}
        for code in self.modes:
            todo, seen = [code], []
            while todo:
                m = self.modes[todo.pop()]
                if m.status == "closed":
                    todo += list(m.replaced_by)
                elif m.code not in seen:
                    seen.append(m.code)
            out[code] = sorted(seen)
        return out

    def validate(self):
        """Problems that block a release: untested, unplaced or ownerless open modes, dangling replacements."""
        probs = []
        for m in self.modes.values():
            if m.status in ("active", "provisional"):
                for f in ("test", "owner"):
                    if not getattr(m, f):
                        probs.append(f"{m.code}: no {f}")
                if not m.layer:
                    probs.append(f"{m.code}: no layer")
            for r in m.replaced_by:
                if r not in self.modes:
                    probs.append(f"{m.code}: replaced_by unknown {r}")
            if m.status == "closed" and not m.replaced_by:
                probs.append(f"{m.code}: closed with nowhere to go")
        return probs

    # ---- persistence
    def to_json(self):
        return json.dumps({"version": self.version, "digest": self.digest(),
                           "modes": [asdict(m) for m in sorted(self.modes.values(), key=lambda m: m.code)]},
                          indent=1)

    @classmethod
    def from_json(cls, s):
        d = json.loads(s)
        return cls(d["version"], {m["code"]: Mode(**m) for m in d["modes"]})


# ---- measurement

def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    m = (p + z * z / (2 * n)) / (1 + z * z / n)
    return (max(0.0, m - c), min(1.0, m + c))


def coverage(labels):
    """labels: [{code or None, fit: bool}] for failing traces.
    naive  = share given any code; fitted = share whose code's inclusion test was answered yes."""
    n = len(labels)
    coded = sum(1 for l in labels if l["code"])
    fitted = sum(1 for l in labels if l["code"] and l["fit"])
    return {"failing": n, "coded": coded, "fitted": fitted,
            "naive": coded / n if n else 1.0, "fitted_share": fitted / n if n else 1.0,
            "fitted_ci": wilson(fitted, n)}


def new_mode_rate(labels, traces_read):
    """Failing traces with no fitting mode, per trace read."""
    k = sum(1 for l in labels if not (l["code"] and l["fit"]))
    return k / traces_read, wilson(k, traces_read)


def kappa(a, b):
    """Cohen's kappa for two coders' labels on the same items (None counts as its own label)."""
    assert len(a) == len(b) and a
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def fisher_greater(k1, n1, k0, n0):
    """One-sided Fisher exact p-value that rate k1/n1 exceeds k0/n0."""
    K, N = k1 + k0, n1 + n0
    def h(x):
        return math.comb(K, x) * math.comb(N - K, n1 - x) / math.comb(N, n1)
    return sum(h(x) for x in range(k1, min(K, n1) + 1))


def drift(before, after, alpha=0.05):
    """before/after: {code: (failing traces with that code, traces read in its flow)}.
    Flags codes whose share rose (absorption or a new cause) or fell to zero (retirement candidate)."""
    out = []
    for code in sorted(set(before) | set(after)):
        k0, n0 = before.get(code, (0, 1))
        k1, n1 = after.get(code, (0, 1))
        p_up = fisher_greater(k1, n1, k0, n0)
        p_down = fisher_greater(k0, n0, k1, n1)
        flag = "rose" if p_up < alpha else ("fell" if p_down < alpha else "")
        out.append({"code": code, "before": (k0, n0), "after": (k1, n1), "p_up": p_up, "p_down": p_down, "flag": flag})
    return out


STOP = set("the a an to of and for in on was is it be not but by with when as at that this compass "
           "borrower asked said".split())


def tokens(note):
    return {w.strip(".,;:'\"()").lower() for w in note.split()} - STOP - {""}


def jaccard(x, y):
    return len(x & y) / len(x | y) if x | y else 1.0


def clusters(notes, threshold=0.15):
    """Single-linkage clusters of free-text notes by token Jaccard similarity: [[index, ...], ...]."""
    toks = [tokens(n) for n in notes]
    parent = list(range(len(notes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            if jaccard(toks[i], toks[j]) >= threshold:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(len(notes)):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]))


def clean_traces_to_retire(bound, conf=0.95):
    """Smallest n with zero occurrences whose one-sided upper bound on the rate is below `bound`."""
    return math.ceil(math.log(1 - conf) / math.log(1 - bound))


def zero_bound(n, conf=0.95):
    """Exact one-sided upper bound on a rate after zero occurrences in n traces."""
    return 1 - (1 - conf) ** (1 / n)


def check_coverage(taxonomy, checks, weights=None):
    """Share of open modes with at least one check at their lowest layer (or lower).
    checks: {code: [layer, ...]}; weights: {code: failing traces} for the failure-weighted share."""
    open_ = taxonomy.active()
    have = [m for m in open_ if any(l <= m.layer for l in checks.get(m.code, []))]
    out = {"modes": len(open_), "with_check": len(have), "share": len(have) / len(open_),
           "missing": [m.code for m in open_ if m not in have]}
    if weights:
        tot = sum(weights.get(m.code, 0) for m in open_)
        out["weighted_share"] = sum(weights.get(m.code, 0) for m in have) / tot if tot else 1.0
    return out
