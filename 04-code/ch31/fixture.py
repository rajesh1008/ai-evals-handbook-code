"""SIMULATED hardship statistics fixture for Chapter 31 (seed 2031)."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2031
N_BOARD = 2400  # Victor's board set
N_PAIR = 400
SLICES = ["common", "uncommon", "hard", "adversarial"]
WEIGHTS = [0.55, 0.25, 0.15, 0.05]

def main():
    rng = random.Random(SEED)
    # Board set: target ~0.375% failures (9/2400)
    fail_ids = set(rng.sample(range(N_BOARD), 9))
    board = []
    for i in range(N_BOARD):
        sl = rng.choices(SLICES, WEIGHTS)[0]
        board.append({
            "trace_id": f"t-{330101 + i}",
            "slice": sl,
            "fail": i in fail_ids,
        })
    # Force named teaching failures
    board[0]["fail"] = True
    board[0]["trace_id"] = "t-330101"
    board[0]["slice"] = "hard"
    # Paired experiment: same cases, baseline vs candidate
    # Construct so unpaired (shuffled groups) looks like a gain but paired diffs near zero / CI includes 0
    paired = []
    for i in range(N_PAIR):
        # mostly both pass; some both fail; some discordant that cancel
        base = rng.random() > 0.12
        if i < 40:
            # discordant both ways equally
            base = i % 2 == 0
            cand = not base
        elif i < 60:
            base = False
            cand = False
        else:
            cand = base if rng.random() > 0.05 else (rng.random() > 0.5)
        paired.append({
            "case_id": f"p-{i:04d}",
            "baseline_pass": base,
            "candidate_pass": cand,
            "slice": rng.choice(SLICES[:3]),
        })
    # Multiplicity toy p-values for 8 metrics (SIMULATED)
    raw_p = [0.01, 0.04, 0.03, 0.20, 0.15, 0.02, 0.08, 0.45]
    digest = hashlib.sha256(json.dumps({"board": [(x["trace_id"], x["fail"]) for x in board], "paired": paired}, sort_keys=True).encode()).hexdigest()[:12]
    payload = {
        "kind": "SIMULATED",
        "seed": SEED,
        "digest": digest,
        "n_board": N_BOARD,
        "n_pair": N_PAIR,
        "board": board,
        "paired": paired,
        "raw_p_values": raw_p,
        "metric_names": ["fee_text", "hardship_text", "tool_ok", "schema_ok", "authority", "grounding", "latency_ok", "cost_ok"],
        "target_hardship": 0.005,
    }
    (OUT / "fixture.json").write_text(json.dumps(payload))
    print(json.dumps({"n_board": N_BOARD, "n_fail": sum(1 for x in board if x["fail"]), "digest": digest}, indent=2))

if __name__ == "__main__":
    main()
