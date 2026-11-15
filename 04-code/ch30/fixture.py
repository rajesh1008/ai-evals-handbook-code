"""SIMULATED gateway migration fixtures for Chapter 30. Seed 2026."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2026
N = 300  # paired cases across two model pins

def main():
    rng = random.Random(SEED)
    baseline_id = "compass-llm-2028-06"
    candidate_id = "compass-llm-2028-09"
    rows = []
    # metrics per case: hardship_ok, fee_ok, latency_ms (lower better for cost proxy)
    for i in range(1, N + 1):
        # baseline strengths
        b_hard = rng.random() < 0.86
        b_fee = rng.random() < 0.91
        b_lat = rng.gauss(820, 90)
        # candidate: hardship improves, fee improves, latency regresses (slower)
        c_hard = b_hard if rng.random() < 0.7 else (rng.random() < 0.92)
        if not b_hard and rng.random() < 0.45:
            c_hard = True
        c_fee = b_fee if rng.random() < 0.75 else (rng.random() < 0.94)
        if not b_fee and rng.random() < 0.4:
            c_fee = True
        c_lat = b_lat * rng.uniform(1.05, 1.25)  # slower
        rows.append({
            "case_id": f"g-330{i:04d}",
            "baseline_model": baseline_id,
            "candidate_model": candidate_id,
            "baseline": {"hardship_ok": int(b_hard), "fee_ok": int(b_fee), "latency_ms": round(b_lat, 1)},
            "candidate": {"hardship_ok": int(c_hard), "fee_ok": int(c_fee), "latency_ms": round(c_lat, 1)},
            "simulated": True,
        })
    # mid-run upgrade plant: a run log that flips model id halfway
    midrun = [baseline_id] * 150 + [candidate_id] * 150
    canary = []
    for j in range(40):
        label = f"canary-{j:02d}"
        s0 = 1 if rng.random() < 0.9 else 0
        # silent change: 6 canaries flip under same version string
        s1 = 1 - s0 if j < 6 else s0
        canary.append({"label": label, "score": s0, "pass": 0, "version_string": "compass-llm-2028-06"})
        canary.append({"label": label, "score": s1, "pass": 1, "version_string": "compass-llm-2028-06"})
    blob = json.dumps({"seed": SEED, "n": N, "rows": rows, "midrun": midrun}, sort_keys=True)
    digest = hashlib.sha256(blob.encode()).hexdigest()[:12]
    out = {
        "seed": SEED,
        "n": N,
        "digest": digest,
        "baseline_model": baseline_id,
        "candidate_model": candidate_id,
        "deprecation_notice_days": 60,
        "named_hold_metric": "latency_ms",
        "simulated_note": "All migration scores are SIMULATED fixtures.",
        "rows": rows,
        "midrun_models": midrun,
        "canary_repeats": canary,
    }
    (OUT / "fixture.json").write_text(json.dumps(out, indent=2))
    print({k: out[k] for k in out if k not in ("rows", "midrun_models", "canary_repeats")})

if __name__ == "__main__":
    main()
