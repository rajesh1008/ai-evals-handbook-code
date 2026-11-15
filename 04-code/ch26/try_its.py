"""Three Try Its: pdf-only, photo-only, voice WER threshold uselessness."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.multimodal import wer, voice_task_table

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
LAB = json.loads((OUT / "lab.json").read_text())

pdf_n = sum(1 for d in FIX["documents"] if d["channel"]=="pdf_upload")
photo_n = sum(1 for d in FIX["documents"] if d["channel"]=="photo")

# Voice: if we gate on WER<0.1 we still miss planted task fails
rows = []
for v in FIX["voice"]:
    rows.append({"wer": wer(v["ref"], v["hyp"]), "task_ok": v["task_ok"]})
gate_wer = [r for r in rows if r["wer"] < 0.1]
missed = sum(1 for r in gate_wer if not r["task_ok"])

out = {
    "try1_channel_mix": {"pdf": pdf_n, "photo": photo_n},
    "try2_clean_vs_glare": {
        "clean_e2e": LAB["clean_e2e"],
        "glare_e2e": LAB["glare_e2e"],
        "drop": LAB["clean_e2e"] - LAB["glare_e2e"],
    },
    "try3_wer_gate": {"n_wer_lt_0_1": len(gate_wer), "task_fails_inside_gate": missed},
}
(OUT / "try_its.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
