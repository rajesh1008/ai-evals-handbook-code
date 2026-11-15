"""Failure injection: holiday-weekend guardrail trip on treatment arm."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.liveexp import refine_guardrail

OUT = Path(__file__).parent / "out"

def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    # Copy treatment errors and plant a holiday spike in indices 100..139 (weekend burst)
    t = list(fix["treatment_errors"])
    for i in range(100, 140):
        t[i] = 1  # force errors over holiday window
    k = sum(t[:140])
    n = 140
    g = refine_guardrail(k, n, target=fix["target"])
    # Force teaching trip if spike present
    if k >= 8:
        g["trip"] = True
        g["trip_reason"] = "holiday_weekend_spike"
    out = {
        "kind": "SIMULATED_INJECTION",
        "name": "holiday_weekend_guardrail",
        "window": fix["holiday_weekend"],
        "n": n,
        "k_errors": k,
        "rate": k / n,
        "guardrail": g,
        "arm_stopped": "treatment",
        "caught": bool(g["trip"]),
        "action": "stop_treatment_arm_early",
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
