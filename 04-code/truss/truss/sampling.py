"""Chapter 3: four sampling strategies and a manifest that makes a sample reproducible.

frame: list of dicts with at least trace_id. Every strategy returns
[(trace_id, weight)], where weight is the inverse inclusion probability, so a
rate estimated from any of them can be weighted back to the population.
"""
import hashlib
import json
import random


def uniform(frame, n, seed=2026):
    rng = random.Random(seed)
    ids = sorted(r["trace_id"] for r in frame)
    w = len(ids) / n
    return [(t, w) for t in sorted(rng.sample(ids, n))]


def stratified(frame, key, quotas, seed=2026):
    rng = random.Random(seed)
    out = []
    for stratum, n in quotas.items():
        ids = sorted(r["trace_id"] for r in frame if r[key] == stratum)
        take = min(n, len(ids))
        out += [(t, len(ids) / take) for t in sorted(rng.sample(ids, take))]
    return out


def inclusion_probs(weights, n):
    """Probabilities proportional to weight, capped at 1, summing to n."""
    p = {k: 0.0 for k in weights}
    fixed, budget = set(), n
    while True:
        free = {k: w for k, w in weights.items() if k not in fixed}
        total = sum(free.values())
        over = [k for k, w in free.items() if budget * w / total >= 1]
        if not over:
            for k, w in free.items():
                p[k] = budget * w / total
            for k in fixed:
                p[k] = 1.0
            return p
        fixed.update(over)
        budget = n - len(fixed)


def risk_weighted(frame, n, risk, seed=2026):
    """Poisson sampling with inclusion probability proportional to risk(row)."""
    rng = random.Random(seed)
    p = inclusion_probs({r["trace_id"]: risk(r) for r in frame}, n)
    return [(t, 1 / p[t]) for t in sorted(p) if rng.random() < p[t]]


def incident_seeded(frame, incident_ids, signature, per_incident=10, seed=2026):
    """Incident traces plus look-alikes sharing their signature. Weight None: never pooled."""
    rng = random.Random(seed)
    out = []
    for t in incident_ids:
        sig = signature(next(r for r in frame if r["trace_id"] == t))
        twins = sorted(r["trace_id"] for r in frame if signature(r) == sig and r["trace_id"] != t)
        out += [(t, None)] + [(x, None) for x in sorted(rng.sample(twins, min(per_incident, len(twins))))]
    return list(dict.fromkeys(out))


def hajek(sample, failed):
    """Weighted failure rate: sum(w * fail) / sum(w)."""
    num = sum(w for t, w in sample if failed[t])
    den = sum(w for _, w in sample)
    return num / den


def frame_hash(ids):
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()[:16]


def manifest(name, strategy, params, frame_sql, frame_ids, sample, seed, truss_version):
    return {"sample_id": name, "strategy": strategy, "params": params, "seed": seed,
            "frame_sql": frame_sql, "frame_count": len(frame_ids),
            "frame_sha256": frame_hash(frame_ids), "truss_version": truss_version,
            "trace_ids": [t for t, _ in sample],
            "weights": {t: w for t, w in sample}}


def verify(m, frame_ids):
    """Raise if the frame the manifest was drawn from has changed."""
    h = frame_hash(frame_ids)
    if h != m["frame_sha256"]:
        raise ValueError(f"frame changed: {len(frame_ids)} traces now, {m['frame_count']} "
                         f"when {m['sample_id']} was drawn (hash {h} != {m['frame_sha256']})")
    return True


def dumps(m):
    return json.dumps(m, indent=1, sort_keys=True)
