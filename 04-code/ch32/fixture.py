"""SIMULATED Harbor gate-suite fixture for Ch32 noise floor (seed 2032)."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).parent / "out"
SEED = 2032
N_CASES = 200
N_RUNS = 5
N_TASKS_PASSK = 40
K_TRIALS = 3

def main():
    rng = random.Random(SEED)
    cases = []
    for i in range(N_CASES):
        cases.append({
            "id": f"t-{330100+i}",
            "p_hardship": rng.uniform(0.82, 0.94),
            "p_fee": rng.uniform(0.86, 0.96),
        })
    # Calibrated repeat-run scores (percentage points) so published floor ≈ 1.4
    # half_range = 1.4 on hardship; fee similar.
    hardship = [87.0, 88.5, 89.8, 88.0, 87.4]
    fee = [89.0, 90.5, 91.8, 90.2, 89.6]
    runs = []
    for r in range(N_RUNS):
        runs.append({
            "run": r + 1,
            "hardship_pct": hardship[r],
            "fee_pct": fee[r],
            # case-level SIMULATED flips for canary / figure detail
            "n_hardship_ok": int(round(hardship[r] / 100.0 * N_CASES)),
            "n_fee_ok": int(round(fee[r] / 100.0 * N_CASES)),
        })
    task_trials = []
    for j in range(N_TASKS_PASSK):
        p = rng.uniform(0.55, 0.92)
        trials = [rng.random() < p for _ in range(K_TRIALS)]
        task_trials.append({"task": f"task-{j+1:02d}", "p": round(p, 4), "trials": trials})
    blob = {
        "seed": SEED,
        "simulated": True,
        "label": "SIMULATED",
        "n_cases": N_CASES,
        "n_runs": N_RUNS,
        "cases": cases,
        "runs": runs,
        "task_trials": task_trials,
        "injection": {"inside_floor_drop_pts": 0.8, "outside_floor_drop_pts": 2.5},
        "published_floor_target_pts": 1.4,
        "margin_pts": 0.5,
        "study_window": "Mon 30 Oct 2028 – Mon 27 Nov 2028",
        "scoreboard_date": "Mon 27 Nov 2028",
    }
    raw = json.dumps({"hardship": hardship, "fee": fee, "tasks": [[int(x) for x in t["trials"]] for t in task_trials], "seed": SEED}, sort_keys=True)
    blob["digest"] = hashlib.sha256(raw.encode()).hexdigest()[:12]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fixture.json").write_text(json.dumps(blob, indent=2))
    print(json.dumps({"digest": blob["digest"], "hardship": hardship, "fee": fee}, indent=2))

if __name__ == "__main__":
    main()
