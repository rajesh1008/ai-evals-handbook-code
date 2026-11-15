"""100 SIMULATED hardship document images + voice pilot gold (no PII bytes)."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2026
N = 100
FIELDS = ["gross", "net", "period_end", "employer", "ytd_gross"]
LEVELS = ["clean", "blur", "skew", "glare", "crop", "compression"]

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]

def main():
    rng = random.Random(SEED)
    docs = []
    for i in range(N):
        gold = {
            "gross": round(rng.uniform(800, 4200), 2),
            "net": round(rng.uniform(600, 3200), 2),
            "period_end": f"2028-06-{rng.randint(1,28):02d}",
            "employer": rng.choice(["Desert Ridge Auto", "Camelback Motors", "Saguaro Coffee", "Valley Medical"]),
            "ytd_gross": round(rng.uniform(5000, 45000), 2),
        }
        # some stubs include a negative deduction line for injection later
        gold["deduction"] = round(-rng.uniform(20, 180), 2)
        docs.append({
            "doc_id": f"d-{300001+i}",
            "channel": "photo" if rng.random() < 0.65 else "pdf_upload",
            "gold": gold,
            "capture_ok": rng.random() > 0.04,  # rare capture fail
        })

    # Voice pilot: 40 short fee/hardship turns with reference transcripts (SIMULATED)
    voice = []
    for i in range(40):
        ref = rng.choice([
            "the late fee is twenty five dollars after fifteen days",
            "I need a deferral because my hours were cut",
            "please check the negative deduction on my stub",
            "the grace period is fifteen days not ten",
        ]).split()
        # ASR hyp with controlled WER
        hyp = list(ref)
        n_err = rng.randint(0, max(1, len(ref)//3))
        for _ in range(n_err):
            if not hyp: break
            j = rng.randrange(len(hyp))
            hyp[j] = rng.choice(["uh", "fee", "thirty", "ten", hyp[j]])
        # task_ok: fee amount/grace correct — independent of WER somewhat
        task_ok = rng.random() < (0.78 if n_err <= 1 else 0.55)
        # plant disagreement cells
        voice.append({
            "voice_id": f"v-{301001+i}",
            "ref": ref,
            "hyp": hyp,
            "task_ok": task_ok,
            "channel": "ivr_pilot",
        })

    # Force some low-WER task fails and high-WER task oks for the lesson
    for row in voice[:5]:
        row["hyp"] = list(row["ref"])  # WER ~0
        row["task_ok"] = False
        row["plant"] = "low_wer_task_fail"
    for row in voice[5:10]:
        row["hyp"] = ["um"] * len(row["ref"])
        row["task_ok"] = True
        row["plant"] = "high_wer_task_ok"

    payload = {
        "seed": SEED,
        "n_docs": N,
        "n_voice": len(voice),
        "fields": FIELDS,
        "levels": LEVELS,
        "documents": docs,
        "voice": voice,
        "study_open": "2028-06-19",
        "scoreboard": "2028-07-10",
        "named_car_photo": "d-300017",
        "named_neg_drop": "d-300042",
    }
    payload["digest"] = digest({k: payload[k] for k in ("seed", "n_docs", "n_voice", "fields", "levels")})
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({k: payload[k] for k in ("seed", "n_docs", "n_voice", "digest", "named_car_photo", "named_neg_drop")}, indent=2))

if __name__ == "__main__":
    main()
