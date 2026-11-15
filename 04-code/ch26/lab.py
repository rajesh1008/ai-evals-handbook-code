"""Degrade 100 docs five ways; score layers; voice WER vs task."""
from __future__ import annotations
import json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.multimodal import (
    DEGRADATIONS, layer_outcome, field_match, degrade_effect, wer, voice_task_table,
)
from truss.fields import wilson

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
rng = random.Random(FIX["seed"] + 26)
FIELDS = FIX["fields"]
docs = FIX["documents"]

print("Chapter 26 lab: documents, images and voice")

# Per-level field extraction rates (SIMULATED extractor stand-in)
level_rates = {}
level_tables = {}
for level in FIX["levels"]:
    matches = []
    e2e = 0
    for doc in docs:
        base = 0.93 if doc["channel"] == "pdf_upload" else 0.86
        rate = degrade_effect(level, base)
        # capture fail short-circuits
        cap = doc["capture_ok"] if level != "crop" else doc["capture_ok"] and rng.random() > 0.08
        # recognition ok with probability ~rate
        rec = cap and (rng.random() < rate)
        # interpretation: field match simulation
        pred = dict(doc["gold"])
        if not rec:
            # scramble some fields
            for k in FIELDS:
                if rng.random() < 0.55:
                    if isinstance(pred[k], float):
                        pred[k] = round(pred[k] * rng.uniform(0.9, 1.15), 2)
                    else:
                        pred[k] = str(pred[k]) + "?"
        fm = field_match(pred, doc["gold"], FIELDS)
        interp = fm["rate"] == 1.0
        # if recognition failed, interpretation rarely perfect
        if not rec:
            interp = fm["rate"] >= 0.8 and rng.random() < 0.15
        lo = layer_outcome(cap, rec, interp)
        e2e += int(lo["end_to_end_ok"])
        matches.append(fm["rate"])
    mean_field = sum(matches)/len(matches)
    level_rates[level] = {
        "mean_field_match": mean_field,
        "e2e": e2e/len(docs),
        "e2e_n": e2e,
        "wilson": list(wilson(e2e, len(docs))),
    }
    level_tables[level] = level_rates[level]
    print(f"  {level}: mean field {mean_field:.3f} e2e {e2e}/{len(docs)}")

# Voice
voice_rows = []
for v in FIX["voice"]:
    w = wer(v["ref"], v["hyp"])
    voice_rows.append({"voice_id": v["voice_id"], "wer": w, "task_ok": v["task_ok"], "plant": v.get("plant")})
vt = voice_task_table(voice_rows)
print(f"voice n={vt['n']} mean_wer={vt['mean_wer']:.3f} task_success={vt['task_success']:.3f}")
print(f"  low_wer_task_fail={vt['low_wer_task_fail']} high_wer_task_ok={vt['high_wer_task_ok']}")

L = {
    "seed": FIX["seed"], "digest": FIX["digest"],
    "levels": level_tables,
    "clean_e2e": level_tables["clean"]["e2e"],
    "glare_e2e": level_tables["glare"]["e2e"],
    "crop_e2e": level_tables["crop"]["e2e"],
    "voice": vt,
    "touchpoint": "document extraction on scoreboard; voice pilot separate gold",
}
(OUT / "lab.json").write_text(json.dumps(L, indent=2))
print("wrote lab.json")
