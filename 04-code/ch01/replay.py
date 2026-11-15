"""Chapter 1 Lab: replay the same conversations through Compass several times."""
import os
import random
import sys
from math import comb, sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.store import open_store  # noqa: E402
from compass_sim import PRODUCTION_TEMPERATURE, respond  # noqa: E402


def resolve_temperature():
    """The bug the failure injection exploits: an environment override wins."""
    return float(os.environ.get("COMPASS_TEMPERATURE", PRODUCTION_TEMPERATURE))


def pick_conversations(db, n=20, seed=2026):
    ids = [r[0] for r in db.execute("SELECT trace_id FROM traces ORDER BY trace_id")]
    chosen = sorted(random.Random(seed).sample(ids, n))
    flows = dict(db.execute(
        f"SELECT trace_id, flow FROM traces WHERE trace_id IN ({','.join('?' * n)})", chosen))
    return [(t, flows[t]) for t in chosen]


def replay(convs, runs=3, temperature=None):
    """Return {trace_id: [reply, reply, ...]} with one reply per run."""
    out = {t: [] for t, _ in convs}
    for run in range(1, runs + 1):
        temp = resolve_temperature() if temperature is None else temperature
        for t, flow in convs:
            out[t].append(respond(t, flow, temp, run))
    return out


def check_manifest(results):
    """Refuse to compare runs made under different sampling settings."""
    temps = {r["temperature"] for replies in results.values() for r in replies}
    if len(temps) > 1:
        raise ValueError(f"runs used different temperatures: {sorted(temps)}")
    return temps.pop()


def pass_rate(results, run):
    verdicts = [replies[run - 1]["verdict"] for replies in results.values()]
    return verdicts.count("pass"), len(verdicts)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def flipped(results):
    """Conversations whose verdict was not the same in every run."""
    return [t for t, rs in results.items() if len({r["verdict"] for r in rs}) > 1]


def pass_at_k(results, k):
    """Share of conversations passed at least once in k tries (unbiased estimate)."""
    tot = 0.0
    for rs in results.values():
        m, c = len(rs), sum(r["verdict"] == "pass" for r in rs)
        tot += 1 - comb(m - c, k) / comb(m, k)
    return tot / len(results)


def pass_hat_k(results, k):
    """Share of conversations passed in all of k tries (pass^k, unbiased estimate)."""
    tot = 0.0
    for rs in results.values():
        m, c = len(rs), sum(r["verdict"] == "pass" for r in rs)
        tot += comb(c, k) / comb(m, k)
    return tot / len(results)
