"""Build 300 SIMULATED hardship conversations + 100 real-transcript summary stats."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2026
N = 300
N_REAL = 100  # summarised real-transcript cohort (SIMULATED labels from production sample)

PERSONAS = [
    ("urgent_parent", 0.22, 0.28),   # id, share, pushback propensity
    ("polite_deferrer", 0.18, 0.02),  # never pushes back — injection target
    ("detail_checker", 0.20, 0.35),
    ("spanish_first", 0.12, 0.22),
    ("returning_caller", 0.15, 0.18),
    ("sceptical_auditor", 0.13, 0.42),
]

GOALS = ["deferral", "extension", "payment_plan", "hardship_packet", "refer_officer"]

def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]

def build_turns(rng, persona_id, push_p, goal, *, force_polite=False):
    n_turns = rng.randint(3, 11)
    turns = []
    met = False
    abandoned = False
    for i in range(1, n_turns + 1):
        role = "user" if i % 2 == 1 else "assistant"
        pb = False
        if role == "user":
            p = 0.0 if force_polite or persona_id == "polite_deferrer" else push_p
            pb = rng.random() < p
        outcome = None
        goal_met = False
        # resolve late if not abandoned
        if i == n_turns and role == "assistant":
            # base success depends on persona cooperation and pushback presence
            base = 0.78
            if persona_id == "polite_deferrer":
                base = 0.91  # looks good — hides wrong offers later
            if persona_id == "sceptical_auditor":
                base = 0.70
            if force_polite:
                base = 0.93
            if rng.random() < base:
                outcome = "resolved"
                goal_met = True
                met = True
            elif rng.random() < 0.45:
                outcome = "abandoned"
                abandoned = True
            else:
                outcome = "unresolved"
        turns.append({
            "i": i, "role": role, "pushback": pb, "goal_met": goal_met,
            "outcome": outcome, "goal": goal,
        })
    return turns, met, abandoned

def main():
    rng = random.Random(SEED)
    # allocate personas
    counts = {p[0]: int(round(p[1] * N)) for p in PERSONAS}
    # fix rounding to exactly N
    while sum(counts.values()) > N:
        counts[max(counts, key=counts.get)] -= 1
    while sum(counts.values()) < N:
        counts[max(counts, key=counts.get)] += 1

    convs = []
    tid = 280001
    for persona_id, share, push_p in PERSONAS:
        for _ in range(counts[persona_id]):
            goal = rng.choice(GOALS)
            turns, met, aband = build_turns(rng, persona_id, push_p, goal)
            user_turns = [t for t in turns if t["role"] == "user"]
            n_pb = sum(1 for t in user_turns if t["pushback"])
            convs.append({
                "trace_id": f"t-{tid}",
                "persona": persona_id,
                "goal": goal,
                "turns": turns,
                "n_turns": len(turns),
                "goal_completed": met,
                "abandoned": aband,
                "turns_to_resolution": next((t["i"] for t in turns if t.get("goal_met")), None),
                "pushback_rate": (n_pb / len(user_turns)) if user_turns else 0.0,
                "source": "simulated",
            })
            tid += 1

    # Real-transcript cohort (SIMULATED production sample summaries, not live PII)
    real_rng = random.Random(SEED + 7)
    real = []
    for i in range(N_REAL):
        # real users push back more; goal completion lower
        n_user = real_rng.randint(2, 6)
        n_pb = sum(1 for _ in range(n_user) if real_rng.random() < 0.31)
        completed = real_rng.random() < 0.79
        aband = (not completed) and real_rng.random() < 0.55
        turns_res = real_rng.randint(4, 10) if completed else None
        real.append({
            "trace_id": f"r-{290001 + i}",
            "n_user_turns": n_user,
            "pushback_rate": n_pb / n_user,
            "goal_completed": completed,
            "abandoned": aband,
            "turns_to_resolution": turns_res,
            "mean_user_words": real_rng.randint(12, 48),
            "disclosure_turn": real_rng.randint(1, 3),
            "source": "real_sample_summary",
        })

    # Target touchpoints: sim ~84%, real ~79% — adjust by flipping few sim outcomes if needed
    def rate(xs, key="goal_completed"):
        return sum(1 for x in xs if x[key]) / len(xs)

    # nudge sim toward 0.84 without breaking persona story
    target_sim = 0.84
    while abs(rate(convs) - target_sim) > 0.005:
        # flip unresolved polite or urgent
        candidates = [c for c in convs if c["persona"] != "sceptical_auditor"]
        c = rng.choice(candidates)
        if rate(convs) < target_sim and not c["goal_completed"]:
            c["goal_completed"] = True
            c["abandoned"] = False
            c["turns_to_resolution"] = c["n_turns"]
            c["turns"][-1]["goal_met"] = True
            c["turns"][-1]["outcome"] = "resolved"
        elif rate(convs) > target_sim and c["goal_completed"] and c["persona"] != "polite_deferrer":
            c["goal_completed"] = False
            c["turns_to_resolution"] = None
            c["turns"][-1]["goal_met"] = False
            c["turns"][-1]["outcome"] = "unresolved"

    # real toward 0.79
    target_real = 0.79
    while abs(rate(real) - target_real) > 0.005:
        c = real_rng.choice(real)
        if rate(real) < target_real and not c["goal_completed"]:
            c["goal_completed"] = True
            c["abandoned"] = False
            c["turns_to_resolution"] = c["turns_to_resolution"] or 6
        elif rate(real) > target_real and c["goal_completed"]:
            c["goal_completed"] = False
            c["turns_to_resolution"] = None

    payload = {
        "seed": SEED,
        "n": N,
        "n_real": N_REAL,
        "persona_counts": counts,
        "sim_goal_completion": rate(convs),
        "real_goal_completion": rate(real),
        "conversations": convs,
        "real_transcripts": real,
        "named_polite": next(c["trace_id"] for c in convs if c["persona"] == "polite_deferrer"),
        "id_range": [convs[0]["trace_id"], convs[-1]["trace_id"]],
        "study_open": "2028-05-15",
        "scoreboard": "2028-06-12",
    }
    payload["digest"] = digest({k: payload[k] for k in ("seed", "n", "persona_counts", "sim_goal_completion", "real_goal_completion")})
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({k: payload[k] for k in ("seed", "n", "digest", "sim_goal_completion", "real_goal_completion", "persona_counts", "named_polite", "id_range")}, indent=2))

if __name__ == "__main__":
    main()
