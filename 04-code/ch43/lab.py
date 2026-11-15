"""Chapter 43 lab: hardship gate on each platform adapter (offline)."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "truss"))

from truss.toolscape import (  # noqa: E402
    PLATFORMS, run_all_platforms, inject_judge_version_drift,
    capability_matrix, recommendation_rows, digest_payload,
    HARDSHIP_WRONG_OFFER_CEILING,
)
from fixture import build_cases, SEED  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

PINNED_JUDGE = "harbor-hardship-judge@2026-11-01"
DEFAULT_DRIFT_JUDGE = "platform-default-judge@unpinned"


def main() -> dict:
    cases = build_cases()
    receipts = run_all_platforms(cases, PINNED_JUDGE)
    inject = inject_judge_version_drift(
        cases,
        pinned_version=PINNED_JUDGE,
        default_version=DEFAULT_DRIFT_JUDGE,
        platform="langsmith",
    )
    payload = {
        "seed": SEED,
        "simulated": True,
        "label": "offline_adapters_plus_SIM_inject",
        "ceiling": HARDSHIP_WRONG_OFFER_CEILING,
        "pinned_judge_version": PINNED_JUDGE,
        "platforms": PLATFORMS,
        "receipts": {k: v.to_dict() for k, v in receipts.items()},
        "all_pinned_admit": all(r.admit for r in receipts.values()),
        "inject": inject,
        "capability_matrix": capability_matrix(),
        "recommendations": recommendation_rows("2026-11-09"),
        "ch16_ceiling_immutable": {
            "charged_usd": 6.191862,
            "unknown_reserve_usd": 0.050079,
            "headroom_usd": 0.05,
            "safe_ceiling_usd": 6.291941,
            "order_not_decide": True,
        },
        "hosted_platform_runs": "PENDING — no paid API; adapters are offline contracts",
    }
    payload["digest"] = digest_payload({
        "seed": SEED,
        "receipts": payload["receipts"],
        "inject_gate_changed": inject["gate_changed"],
        "extra": inject["extra_wrong_offers"],
    })
    (OUT / "lab.json").write_text(json.dumps(payload, indent=2))
    (OUT / "inject.json").write_text(json.dumps(inject, indent=2))
    (OUT / "fixture.json").write_text(json.dumps({"seed": SEED, "n": len(cases), "wrong_offers": 0}, indent=2))
    return payload


if __name__ == "__main__":
    p = main()
    print("digest", p["digest"])
    print("all_pinned_admit", p["all_pinned_admit"])
    print("inject gate_changed", p["inject"]["gate_changed"], "extra", p["inject"]["extra_wrong_offers"])
