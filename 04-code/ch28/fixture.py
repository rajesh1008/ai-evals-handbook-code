"""SIMULATED reviewer decisions for Chapter 28. Seed 2026. Not real-human data."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2026
N = 500

def main():
    rng = random.Random(SEED)
    rows = []
    # R-ryan: 250 reviews, exactly 1 override => 0.4%
    # Others: 250 reviews split across four officers
    others = ["R-grace", "R-ben", "R-marisol", "R-daniel"]
    wrong_plant_ids = set(range(1, 21))
    ryan_override_at = 137  # one of ryan's local indices

    for i in range(1, N + 1):
        if i <= 250:
            rid = "R-ryan"
            local = i
            ov_forced = (local == ryan_override_at)
            med_t = 6.0
        else:
            rid = others[(i - 251) % 4]
            local = i
            ov_forced = None
            med_t = {"R-grace": 28.0, "R-ben": 22.0, "R-marisol": 25.0, "R-daniel": 20.0}[rid]

        gold = 1 if rng.random() < 0.88 else 0
        ai_wrong = i in wrong_plant_ids
        if ai_wrong:
            ai_label = 1 - gold
        else:
            ai_label = gold if rng.random() < 0.92 else 1 - gold

        if rid == "R-ryan":
            overrode = ov_forced
            if overrode:
                human = 1 - ai_label
            else:
                # rubber-stamp: follow AI; automation bias on wrong plants
                if ai_wrong and rng.random() < 0.8:
                    human = ai_label
                else:
                    human = ai_label
            approval_seconds = max(2.5, med_t * rng.lognormvariate(0, 0.25))
        else:
            ov_p = {"R-grace": 0.20, "R-ben": 0.12, "R-marisol": 0.16, "R-daniel": 0.11}[rid]
            overrode = rng.random() < ov_p
            if overrode:
                human = 1 - ai_label
            else:
                if ai_wrong and rng.random() < 0.30:
                    human = ai_label
                else:
                    human = gold if rng.random() < 0.9 else ai_label
            approval_seconds = max(5.0, med_t * rng.lognormvariate(0, 0.35))
            # mild fatigue: later items slightly worse agreement by flipping some
            if i > 400 and rng.random() < 0.08 and human == gold:
                human = 1 - human
                overrode = human != ai_label

        rows.append({
            "decision_id": f"d-320{i:04d}",
            "trace_id": f"t-{310500 + i}",
            "reviewer_id": rid,
            "gold": gold,
            "ai_label": ai_label,
            "ai_wrong": bool(ai_wrong),
            "saw_ai": True,
            "human_label": human,
            "final_label": human,
            "overrode": bool(overrode),
            "approval_seconds": round(approval_seconds, 2),
            "queue_position": i,
            "kind": "wrong_plant" if ai_wrong else "ordinary",
            "simulated": True,
        })

    blob = json.dumps({"seed": SEED, "n": N, "rows": rows}, sort_keys=True)
    digest = hashlib.sha256(blob.encode()).hexdigest()[:12]
    by_rev = {}
    for r in rows:
        by_rev[r["reviewer_id"]] = by_rev.get(r["reviewer_id"], 0) + 1
    ryan_ov = sum(1 for r in rows if r["reviewer_id"]=="R-ryan" and r["overrode"])
    out = {
        "seed": SEED,
        "n": N,
        "digest": digest,
        "kind_counts": {
            "ordinary": sum(1 for r in rows if r["kind"]=="ordinary"),
            "wrong_plant": sum(1 for r in rows if r["kind"]=="wrong_plant"),
        },
        "reviewer_counts": by_rev,
        "named_rubber": "R-ryan",
        "ryan_override_rate": ryan_ov / by_rev["R-ryan"],
        "named_plant": "d-3200001",
        "simulated_note": "All reviewer decisions are SIMULATED; not real-human study data.",
        "rows": rows,
    }
    (OUT / "fixture.json").write_text(json.dumps(out, indent=2))
    print({k: out[k] for k in out if k != "rows"})

if __name__ == "__main__":
    main()
