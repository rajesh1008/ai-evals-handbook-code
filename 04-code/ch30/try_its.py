from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.gateway import migration_delta, release_decision, deprecation_plan

OUT = Path(__file__).parent / "out"

def main():
    lab = json.loads((OUT / "lab.json").read_text())
    b, c = lab["baseline_rates"], lab["candidate_rates"]
    # 1: ignore latency — would falsely SHIP
    d1 = migration_delta({"hardship_ok": b["hardship_ok"], "fee_ok": b["fee_ok"]},
                         {"hardship_ok": c["hardship_ok"], "fee_ok": c["fee_ok"]})
    # 2: require 90-day notice
    p90 = deprecation_plan(90, True, lab["decision"]["decision"]=="HOLD")
    p45 = deprecation_plan(45, True, False)
    # 3: flip latency to improved artificially
    c2 = dict(c); c2["latency_ms"] = b["latency_ms"] * 0.95
    d3 = migration_delta(b, c2)
    rows = []
    for r in d3["rows"]:
        rr=dict(r)
        if r["metric"]=="latency_ms":
            rr["delta"]=r["baseline"]-r["candidate"]
        rows.append(rr)
    out = {
        "try1_ignore_latency_decision": release_decision(d1["rows"]),
        "try2_notice_windows": {"days90": p90, "days45": p45},
        "try3_if_latency_improved": release_decision(rows),
        "baseline_hold": lab["decision"],
        "simulated": True,
    }
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
