"""SIMULATED comparative-eval fixture for Chapter 42. No paid API."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2042
N = 600


def _systems(rng: random.Random):
    # Binary wrong-fee-explanation outcomes (1=fail) on the SAME 600 fee traces.
    # Paired ranking target: prompt_v2 < small_fee_model < prompt_v1 < prompt_v3.
    # SLM cost 1/3 of frontier prompts; hardship NOT assigned to SLM (policy).
    # Construct fails by index sets so rates are exact and reproducible.
    idx = list(range(N))
    rng.shuffle(idx)

    def marks(k):
        s = set(idx[:k])
        return [1 if i in s else 0 for i in range(N)]

    # Exact failure counts on shared alignment
    p2 = marks(6)     # 1.00%
    slm = marks(8)    # 1.33% — near v2, still under a loose narrative
    p1 = marks(12)    # 2.00%
    p3 = marks(24)    # 4.00%
    return {
        "prompt_v1": p1,
        "prompt_v2": p2,
        "prompt_v3": p3,
        "small_fee_model": slm,
    }


def main():
    rng = random.Random(SEED)
    systems = _systems(rng)
    costs = {
        "prompt_v1": 0.90,   # USD per 1k fee traces (SIMULATED token bill)
        "prompt_v2": 0.90,
        "prompt_v3": 0.90,
        "small_fee_model": 0.30,  # third the cost
        "frontier_hardship": 2.40,  # hardship stays frontier — not in fee compare
    }
    payload = {
        "seed": SEED,
        "simulated": True,
        "label": "SIMULATED",
        "n_paired": N,
        "flow": "fee_explanation",
        "systems_binary_fail": {k: v for k, v in systems.items() if k != "latent_hard"},
        "costs_usd_per_1k": costs,
        "policy": {
            "hardship_route": "frontier_only",
            "fee_small_model_candidate": True,
            "wrong_fee_target": 0.02,
            "wrong_hardship_target": 0.005,
        },
        "router_sim": {
            "n": 2000,
            "route_accuracy": 0.71,
            "oracle_accuracy": 0.89,
            "cost_per_query_usd": 0.0012,
            "note": "SIMULATED router component study — not a live bench run",
        },
    }
    raw = json.dumps({k: payload[k] for k in payload if k != "digest"}, sort_keys=True).encode()
    payload["digest"] = hashlib.sha256(raw).hexdigest()[:12]
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2))
    print(payload["digest"], N)
    return payload


if __name__ == "__main__":
    main()
