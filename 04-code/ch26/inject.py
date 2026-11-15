"""Failure injection: transcription drops negative amounts → wrong net."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.multimodal import drop_negative_amounts, field_match

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())

# Build a stub transcript line including a negative deduction
doc = next(d for d in FIX["documents"] if d["doc_id"] == FIX["named_neg_drop"])
g = doc["gold"]
text = f"gross {g['gross']} net {g['net']} deduction {g['deduction']} employer {g['employer']}"
mut = drop_negative_amounts(text)
# naive parse after mutation: deduction becomes positive → net mis-read
import re
def grab(label, s):
    m = re.search(rf'{label} (-?\d+\.\d+)', s)
    return float(m.group(1)) if m else None

pred = {
    "gross": grab("gross", mut),
    "net": grab("net", mut),
    "period_end": g["period_end"],
    "employer": g["employer"],
    "ytd_gross": g["ytd_gross"],
}
# interpretation error: deduction sign flip confuses net check
gold_fields = {k: g[k] for k in FIX["fields"]}
fm = field_match(pred, gold_fields, FIX["fields"])

result = {
    "named": FIX["named_neg_drop"],
    "original_snippet": text,
    "mutated_snippet": mut,
    "deduction_gold": g["deduction"],
    "sign_flipped": "-" not in mut.split("deduction")[-1][:12],
    "field_match_rate": fm["rate"],
    "lesson": "Dropping negatives in transcription turns a recognition error into a wrong hardship income read.",
}
(OUT / "inject.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
