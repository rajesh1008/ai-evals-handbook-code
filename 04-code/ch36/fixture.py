from __future__ import annotations
import hashlib, json, random
from pathlib import Path
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2036
N = 400  # per arm eventual capacity; peeks earlier

def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]

def main():
    rng = random.Random(SEED)
    # control error rate ~0.4%; treatment better ~0.25% until holiday spike injection separately
    control = [1 if rng.random() < 0.004 else 0 for _ in range(N)]
    treatment = [1 if rng.random() < 0.0025 else 0 for _ in range(N)]
    # borrower units
    units = [f"b-{900000+i}" for i in range(N * 2)]
    # retrieval rankings for interleaving demo
    control_rank = [f"doc-{i}" for i in range(1, 11)]
    treatment_rank = ["doc-2", "doc-1", "doc-4", "doc-3", "doc-5", "doc-7", "doc-6", "doc-8", "doc-10", "doc-9"]
    clicks = ["doc-2", "doc-4"]
    payload = {
        "kind": "SIMULATED",
        "seed": SEED,
        "n_per_arm_capacity": N,
        "control_errors": control,
        "treatment_errors": treatment,
        "units": units,
        "control_rank": control_rank,
        "treatment_rank": treatment_rank,
        "clicks": clicks,
        "study_window": "2028-11-06 to 2028-12-04",
        "scoreboard_date": "2028-12-04",
        "holiday_weekend": "2028-11-24 to 2028-11-25",
        "primary_metric": "wrong_hardship_offer_rate",
        "guardrail_metric": "wrong_hardship_offer_rate",
        "target": 0.005,
    }
    payload["digest"] = digest({k: payload[k] for k in payload if k not in ("control_errors", "treatment_errors")})
    # include error counts in digest stability via sums
    payload["digest"] = digest({
        "seed": SEED,
        "c_sum": sum(control),
        "t_sum": sum(treatment),
        "n": N,
    })
    (OUT / "fixture.json").write_text(json.dumps(payload))
    print(payload["digest"], sum(control), sum(treatment))

if __name__ == "__main__":
    main()
