"""Chapter 12: datasets. Golden cases with provenance, digests and manifests, version diffs,
near-duplicate and leak scans, slice composition and slice-by-slice gates, sensitivity (minimum
detectable difference), and the rule that graduates progression cases into the regression set.

A case is a plain dict. Required keys: case_id, flow, slice, source, label. Optional keys used
here: trace_id, text, split, policy_version, labelled_on, labelled_by, features, planted.
Sources "incident", "synthetic", "authored" and "planted" never enter a rate (Chapter 3's rule, extended).
"""
import hashlib
import json
import re
from collections import Counter, defaultdict
from math import sqrt

from scipy.stats import norm

from .rates import wilson, upper_bound

SLICES = ("common", "uncommon", "hard", "adversarial", "ood")
NOT_IN_RATES = ("incident", "synthetic", "planted", "authored")
_KEYS = ("case_id", "trace_id", "flow", "slice", "source", "split", "label", "policy_version",
         "labelled_on", "labelled_by", "text")


def case_digest(case):
    """Twelve hex characters over the fields that change what a case measures."""
    body = json.dumps({k: case.get(k) for k in _KEYS}, sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()[:12]


def set_digest(cases):
    """Digest of a whole set: order-free, so a reshuffle does not look like a new set."""
    return hashlib.sha256("".join(sorted(case_digest(c) for c in cases)).encode()).hexdigest()[:12]


def manifest(name, version, cases, notes="", truss_version=None):
    """What a dataset version is: counts by source and slice, digest, and the notes that explain it."""
    return {"name": name, "version": version, "n": len(cases), "digest": set_digest(cases),
            "by_source": dict(sorted(Counter(c["source"] for c in cases).items())),
            "by_slice": {s: sum(c["slice"] == s for c in cases) for s in SLICES},
            "rate_eligible": sum(rate_eligible(c) for c in cases), "notes": notes,
            "truss_version": truss_version}


def diff(old, new):
    """Cases added, removed and changed between two versions, keyed by case_id."""
    a, b = {c["case_id"]: c for c in old}, {c["case_id"]: c for c in new}
    changed = [k for k in a.keys() & b.keys() if case_digest(a[k]) != case_digest(b[k])]
    relabelled = [k for k in changed if a[k]["label"] != b[k]["label"]]
    return {"added": sorted(b.keys() - a.keys()), "removed": sorted(a.keys() - b.keys()),
            "changed": sorted(changed), "relabelled": sorted(relabelled)}


def rate_eligible(case):
    """True when a case may be counted in a pass or failure rate."""
    return case["source"] not in NOT_IN_RATES and not case.get("planted")


def shingles(text, n=3):
    words = re.findall(r"[a-z0-9áéíóúñ$]+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(max(1, len(words) - n + 1))}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def near_duplicates(texts, threshold=0.5, n=3):
    """Pairs (i, j, similarity) of texts whose word n-gram Jaccard reaches the threshold."""
    sh = [shingles(t, n) for t in texts]
    out = []
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            s = jaccard(sh[i], sh[j])
            if s >= threshold:
                out.append((i, j, round(s, 3)))
    return out


def leak_scan(docs, cases, n=8, threshold=0.3, canaries=()):
    """Index documents that contain a golden case: n-gram containment or a canary string.

    docs is {doc_id: text}; cases is a list with "case_id" and "text". Returns a list of
    (doc_id, case_id, containment, canary_hit) for every hit, largest containment first.
    """
    hits = []
    grams = {c["case_id"]: shingles(c["text"], n) for c in cases}
    for did, text in docs.items():
        dg = shingles(text, n)
        canary = any(k in text for k in canaries)
        for cid, g in grams.items():
            cont = len(g & dg) / len(g) if g else 0.0
            if cont >= threshold or (canary and cont > 0):
                hits.append((did, cid, round(cont, 3), canary))
    return sorted(hits, key=lambda h: -h[2])


def composition(cases, rows="flow", cols="slice"):
    """Counts as {row: {col: n}}, for the slice heat map."""
    out = defaultdict(Counter)
    for c in cases:
        out[c[rows]][c[cols]] += 1
    return {r: dict(v) for r, v in sorted(out.items())}


def slice_gate(results, gates):
    """Gate each slice on its own Wilson lower bound.

    results is a list of (slice, passed); gates is {slice: minimum pass rate}. A slice passes
    when the lower end of its Wilson 95% interval is at or above its gate. Returns per-slice rows
    and an overall verdict that is the AND of the slices, not the aggregate.
    """
    rows = {}
    for s, g in gates.items():
        xs = [p for sl, p in results if sl == s]
        k, n = sum(xs), len(xs)
        lo, hi = wilson(k, n)
        rows[s] = {"k": k, "n": n, "rate": k / n if n else None, "lo": lo, "hi": hi, "gate": g,
                   "pass": n > 0 and lo >= g}
    k, n = sum(p for _, p in results), len(results)
    return {"slices": rows, "aggregate": k / n if n else None, "pass": all(r["pass"] for r in rows.values())}


def mdd(n, p=0.9, alpha=0.05, power=0.8):
    """Minimum detectable drop in a pass rate p between two runs of n cases each (two-sided z test)."""
    if n == 0:
        return 1.0
    z = norm.ppf(1 - alpha / 2) + norm.ppf(power)
    return z * sqrt(2 * p * (1 - p) / n)


def slice_bounds(n_by_slice, failures=0):
    """One-sided 95% upper bound on the failure rate each slice could support with the given failures."""
    return {s: upper_bound(failures, n) if n else 1.0 for s, n in n_by_slice.items()}


def graduate(history, k=3):
    """Progression cases that passed in each of the last k runs, ready to join the regression set.

    history is {case_id: [True/False per release candidate, oldest first]}.
    """
    return sorted(c for c, runs in history.items() if len(runs) >= k and all(runs[-k:]))


def stale_labels(cases, changes):
    """Cases whose label predates a policy change that touches their flow and feature.

    changes is a list of {"policy": id, "effective": "YYYY-MM-DD", "flow": f, "feature": name}.
    """
    out = []
    for c in cases:
        for ch in changes:
            if (c["flow"] == ch["flow"] and c.get("features", {}).get(ch["feature"])
                    and str(c.get("labelled_on", "")) < ch["effective"]):
                out.append((c["case_id"], ch["policy"]))
    return out
