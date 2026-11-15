"""Chapter 2: the first stratified sample, as a function over the trace store."""
import random


def stratified_sample(db, quotas, seed=2026):
    rng = random.Random(seed)
    sample = []
    for flow, n in quotas.items():
        ids = [row[0] for row in db.execute(
            "SELECT trace_id FROM traces WHERE flow = ? ORDER BY trace_id", (flow,))]
        sample += sorted(rng.sample(ids, min(n, len(ids))))
    return sample
