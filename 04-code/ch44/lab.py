"""Chapter 44 lab: black-box acceptance on a vendor collections trial (offline)."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "truss"))

from truss.vendorbox import (  # noqa: E402
    trial_api_respond, score_acceptance, inject_demo_overlap,
    claim_anatomy_checklist, public_benchmark_critical_notes, digest_payload,
    HARDSHIP_WRONG_OFFER_CEILING,
)
from fixture import build_cases, SEED, VENDOR_CLAIM_RATE  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


def main() -> dict:
    cases = build_cases()
    responses = {c.case_id: trial_api_respond(c, contaminated_demo=False) for c in cases}
    receipt = score_acceptance(cases, responses, vendor_claim_rate=VENDOR_CLAIM_RATE)
    inject = inject_demo_overlap(cases, vendor_claim_rate=VENDOR_CLAIM_RATE)
    payload = {
        "seed": SEED,
        "simulated": True,
        "label": "offline_vendor_trial_acceptance_plus_SIM_overlap_inject",
        "ceiling": HARDSHIP_WRONG_OFFER_CEILING,
        "vendor_name": "EXAMPLE CollectEase collections assistant",
        "vendor_claim_rate": VENDOR_CLAIM_RATE,
        "n": len(cases),
        "receipt": receipt.to_dict(),
        "inject": inject,
        "decline_purchase": inject["decline_purchase"],
        "claim_checklist": claim_anatomy_checklist(),
        "public_benchmark_notes": public_benchmark_critical_notes(),
        "ch16_ceiling_immutable": {
            "usage_incurred_usd": 6.191862,
            "uncertain_reserve_usd": 0.050079,
            "uncertain_reserve_status": "not_known_spent_or_known_unspent",
            "headroom_usd": 0.05,
            "headroom_status": "not_spent",
            "conservative_ceiling_usd": 6.291941,
            "order_not_decide": True,
        },
        "live_vendor_http": "PENDING — no paid API; trial responses are offline fixtures",
    }
    payload["digest"] = digest_payload({
        "seed": SEED,
        "receipt": payload["receipt"],
        "inject_overlap": inject["overlap_count"],
        "decline": inject["decline_purchase"],
        "rate_moved": inject["rate_moved_toward_claim"],
    })
    (OUT / "lab.json").write_text(json.dumps(payload, indent=2))
    (OUT / "inject.json").write_text(json.dumps(inject, indent=2))
    (OUT / "fixture.json").write_text(json.dumps({"seed": SEED, "n": len(cases), "vendor_claim": VENDOR_CLAIM_RATE}, indent=2))
    return payload


if __name__ == "__main__":
    p = main()
    print("digest", p["digest"])
    print("admit", p["receipt"]["admit"], "wrong", p["receipt"]["wrong_offers"], "/", p["receipt"]["n"])
    print("decline", p["decline_purchase"], "overlap", p["inject"]["overlap_count"])
    print("rate clean→contam", p["inject"]["clean"]["rate"], "→", p["inject"]["contaminated"]["rate"])
