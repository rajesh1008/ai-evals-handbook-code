"""Failure injection: guard latency breaks SMS timeout."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.guardmon import latency_breaks_channel, promote_check_to_guard, run_guard

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    g = promote_check_to_guard("hardship_eligibility_schema", latency_budget_ms=80)
    # injected path ignores budget and reports wall clock that exceeds SMS
    wall = fix["guard_p99_ms_injected"]
    broke = latency_breaks_channel(wall, channel_timeout_ms=fix["sms_timeout_ms"])
    # even a "pass" signal is unusable if the channel timed out first
    run = run_guard({**g, "latency_budget_ms": fix["sms_timeout_ms"]}, signal_pass=True, latency_ms=wall)
    out = {
        "simulated": True,
        "injection": "SMS_TIMEOUT_BREAK",
        "wall_p99_ms": wall,
        "sms_timeout_ms": fix["sms_timeout_ms"],
        "breaks_timeout": broke["breaks_timeout"],
        "run_decision": run["decision"],
        "caught": broke["breaks_timeout"] and run["decision"] == "timeout",
        "lesson": "A guard that answers after the SMS timeout is a production outage, not a safety win.",
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
