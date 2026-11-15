"""Three Try-its for Chapter 41 (deterministic)."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.costknow import (
    waterfall,
    cheap_first_cascade,
    amortise_study,
    cost_per_decision,
)

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    lab = json.loads((OUT / "lab.json").read_text())
    # 1. Recompute waterfall savings
    wf = waterfall(fix["waterfall"])
    t1 = {"name": "waterfall_savings", "saved_usd": wf["saved_usd"], "ok": abs(wf["saved_usd"] - 1260.0) < 1e-9}
    # 2. Cascade without human reads (what-if)
    vols = dict(fix["cascade_volumes"])
    vols["n_ordered_reads"] = 0
    c = cheap_first_cascade(vols, fix["cascade_unit_costs"])
    t2 = {"name": "cascade_calls_only", "total_usd": c["total_usd"], "ok": c["read_usd"] == 0.0}
    # 3. Amortise study across 6 releases instead of 12
    a = amortise_study(fix["ch16"]["charged_usd"], 6)
    cpd = cost_per_decision(640.0, 40)
    t3 = {
        "name": "amortise_and_per_decision",
        "amortised": a["amortised_per_release_usd"],
        "usd_per_decision": cpd["usd_per_decision"],
        "ok": a["amortised_per_release_usd"] > lab["amortisation"]["amortised_per_release_usd"],
    }
    out = {"try_its": [t1, t2, t3], "all_ok": all(t["ok"] for t in (t1, t2, t3))}
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
