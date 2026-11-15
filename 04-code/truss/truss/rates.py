"""Chapter 2: the arithmetic every Truss report uses.

Wilson intervals for pass rates, the exact one-sided upper bound for rare
failures, the sample size a target needs, and traffic weighting.
"""
from math import sqrt

from scipy.stats import beta


def wilson(k, n, z=1.96):
    """Two-sided Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def upper_bound(failures, n, confidence=0.95):
    """Exact (Clopper-Pearson) one-sided upper bound on a failure rate."""
    if failures >= n:
        return 1.0
    return float(beta.ppf(confidence, failures + 1, n - failures))


def traces_needed(target, failures=0, confidence=0.95):
    """Smallest n whose one-sided upper bound falls under target, given failures."""
    n = failures + 1
    while upper_bound(failures, n, confidence) >= target:
        n += 1
    return n


def weighted_rate(per_flow, shares):
    """Weight per-flow pass rates {flow: (k, n)} back to traffic shares."""
    total = sum(shares[f] for f in per_flow)
    return sum(shares[f] / total * k / n for f, (k, n) in per_flow.items())
