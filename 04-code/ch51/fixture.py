"""Ch51 fixture — SIMULATED Toronto telecom offline/online mismatch teaching pack."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2051

CH16 = {
    "usage_incurred_usd": 6.191862,
    "uncertain_reserve_usd": 0.050079,
    "policy_headroom_usd": 0.05,
    "ceiling_usd": 6.291941,
    "note": "kinds under $12 cap; not invoice; not historical cache recovery",
}

# Teaching scenarios — not observed client history
CASES = {
    "hartford": {
        "domain": "prior_authorization",
        "decide_owner": "medical_director",
        "decide_metric": "wrong_denial_rate",
        "taxonomy": ["wrong_deny", "wrong_approve", "missing_evidence", "stale_guideline", "phi_overshare"],
        "offline_n": 800,
        "wrong_denial": 3,
        "guideline_pin": "guide-v4.2",
        "kind": "SIMULATED",
    },
    "manchester": {
        "domain": "returns_agent",
        "decide_owner": "fraud_desk",
        "decide_metric": "refund_accuracy",
        "taxonomy": ["wrong_refund", "missed_fraud", "window_misread", "sku_mismatch", "tone_only_pass"],
        "offline_n": 1200,
        "wrong_refund": 11,
        "fraud_catch_rate": 0.91,
        "kind": "SIMULATED",
    },
    "toronto": {
        "domain": "telecom_billing_support",
        "decide_owner": "billing_sme",
        "decide_metric": "cycle_day_complaint_rate",
        "taxonomy_offline": ["wrong_balance", "plan_mismatch", "handoff_late", "tone_fail"],
        "taxonomy_missing_class": "BillingCycleEdge",
        "offline_pass_rate": 0.9567,
        "online_cycle_day_complaint_pp": None,  # filled from lab online join
        "offline_saw_edge": False,
        "kind": "SIMULATED",
        "failed_practice": True,
    },
    "frankfurt": {
        "domain": "contract_review",
        "decide_owner": "counsel",
        "decide_metric": "false_accept_rate",
        "taxonomy": ["missed_indemnity", "wrong_party", "jurisdiction_skip", "hallucinated_cite", "redline_overreach"],
        "clause_recall": 0.88,
        "counsel_override_rate": 0.14,
        "jurisdiction_pin": "de-gov-law-pack-v3",
        "kind": "SIMULATED",
    },
}

HARBOR_BORROW = [
    {"from_case": "hartford", "borrowed": "oversample_costly_flow", "harbor_artefact": "hardship_quota_100_of_300"},
    {"from_case": "manchester", "borrowed": "adversarial_fraud_slice", "harbor_artefact": "adversarial_stratum_gate"},
    {"from_case": "toronto", "borrowed": "force_include_calendar_edge", "harbor_artefact": "incident_to_card_join"},
    {"from_case": "frankfurt", "borrowed": "decide_owner_outside_eng", "harbor_artefact": "victor_decide_cells"},
]

def _telecom_traces():
    rows = []
    for i in range(1, 301):
        day = (i % 30) + 1
        # Plant mid-cycle plan changes on cycle-day-1 rows so offline/online gap is visible.
        mid = (day == 1 and (i // 30) % 2 == 0) or (i % 19 == 0)
        rows.append({
            "id": f"tt-{i:04d}",
            "day_in_cycle": day,
            "midcycle_change": mid,
            "prorate_needed": mid,
            # Offline labels ignore cycle-day: edge rows still mostly "pass" offline
            "offline_label": "fail" if (i % 23 == 0 and day != 1) else "pass",
            "online_complaint": bool(mid and day == 1),
        })
    return rows

TELECOM_TRACES = _telecom_traces()


def digest_of(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()[:12]


def main():
    payload = {
        "seed": SEED,
        "cases": CASES,
        "harbor_borrow": HARBOR_BORROW,
        "telecom_traces": TELECOM_TRACES,
        "CH16": CH16,
        "SIMULATED": True,
        "live_provider_sweeps": "PENDING",
        "teaching_note": "cameo cities are teaching scenarios; not observed client history",
    }
    # Fingerprint traces so digest moves if the teaching pack's edge planting changes.
    trace_fp = digest_of([
        (r["id"], r["day_in_cycle"], r["midcycle_change"], r["offline_label"], r.get("online_complaint"))
        for r in TELECOM_TRACES
    ])
    d = digest_of({"seed": SEED, "cases": CASES, "borrow": HARBOR_BORROW, "CH16": CH16, "trace_fp": trace_fp})
    payload["digest"] = d
    payload["trace_fp"] = trace_fp
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2) + "\n")
    print("fixture digest", d, "seed", SEED)


if __name__ == "__main__":
    main()
