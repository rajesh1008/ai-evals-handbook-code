"""Deterministic hardship-adjacent fixture (SIMULATED labels).

n=800 so that zero wrong offers yields Wilson upper < 0.005 (Victor's ceiling).
Smaller n cannot clear the ceiling even with zero failures — see Chapter 15.
"""
from __future__ import annotations
import random
from typing import Any, Dict, List

SEED = 2043
N = 800

def build_cases(seed: int = SEED, n: int = N) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    cases = []
    for i in range(n):
        cases.append({
            "id": f"h-{seed}-{i:03d}",
            "flow": "hardship",
            "wrong_offer": False,
            "severity": round(rng.random(), 4),
        })
    return cases
