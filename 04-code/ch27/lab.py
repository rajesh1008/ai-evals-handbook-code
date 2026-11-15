"""Score 500 authority traces; adversarial suite; gate metric."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.authority import (
    permission_trace, forbidden_path_pass, refusal_quality, escalation_correct,
    aggregate_authority, adversarial_suite_summary,
)
from truss.fields import wilson

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())

print("Chapter 27 lab: authority compliance and safety behaviour")
rows = []
refuse_rows = []
esc_rows = []
for tr in FIX["traces"]:
    pt = permission_trace(tr["steps"])
    # trust fixture authority_ok for planted kinds; also recompute
    auth_ok = pt["authority_ok"] and tr["authority_ok"]
    # for clean etc fixture authority_ok is source of truth when steps clean
    if tr["kind"] != "forbidden_path":
        auth_ok = tr["authority_ok"] and pt["authority_ok"]
    else:
        auth_ok = False  # planted
    fp = forbidden_path_pass(tr["outcome_ok"], auth_ok)
    fp["trace_id"] = tr["trace_id"]
    fp["kind"] = tr["kind"]
    rows.append(fp)
    if tr["kind"] in ("refuse_ok", "over_refuse", "under_refuse", "clean") and tr["should_refuse"] or tr["refused"]:
        rq = refusal_quality(tr["refused"], tr["should_refuse"], tr["cited_policy"])
        rq["trace_id"] = tr["trace_id"]
        refuse_rows.append(rq)
    if tr["kind"] in ("escalate_ok", "miss_escalate") or tr["should_escalate"] or tr["escalated"]:
        eq = escalation_correct(tr["escalated"], tr["should_escalate"])
        eq["trace_id"] = tr["trace_id"]
        esc_rows.append(eq)

agg = aggregate_authority(rows)
lo, hi = wilson(agg["n_authority_ok"], agg["n"])
agg["wilson"] = [lo, hi]
print(f"authority compliance {agg['authority_compliance']:.3f} ({agg['n_authority_ok']}/{agg['n']})")
print(f"forbidden_path_passes {agg['forbidden_path_passes']} rate {agg['forbidden_path_rate']:.3f}")

refuse_ok = sum(1 for r in refuse_rows if r["ok"])
esc_ok = sum(1 for r in esc_rows if r["ok"])
print(f"refusal rows {len(refuse_rows)} ok {refuse_ok}; escalation rows {len(esc_rows)} ok {esc_ok}")

adv = adversarial_suite_summary(FIX["adversarial"])
print(f"adversarial catch_rate {adv['catch_rate']:.3f} ({adv['n_caught']}/{adv['n']})")

L = {
    "seed": FIX["seed"], "digest": FIX["digest"],
    "authority": agg,
    "refusal": {"n": len(refuse_rows), "n_ok": refuse_ok, "rate": refuse_ok/max(1,len(refuse_rows))},
    "escalation": {"n": len(esc_rows), "n_ok": esc_ok, "rate": esc_ok/max(1,len(esc_rows))},
    "adversarial": adv,
    "incidents": FIX["incidents"],
    "touchpoint": "authority_compliance on gate tier; two retro incidents",
}
(OUT / "lab.json").write_text(json.dumps(L, indent=2))
print("wrote lab.json")
