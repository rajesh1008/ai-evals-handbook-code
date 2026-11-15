"""Chapter 41 fixture: verified Ch16 study costs + SIM release waterfall inputs."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# Verified primary source: Ch16 NEW run ch16-full-new-2026-11-08-2131
CH16 = {
    "run_id": "ch16-full-new-2026-11-08-2131",
    "cap_usd": 12.0,
    "charged_usd": 6.191862,  # ledger invoice-actual for committed caches
    "unreconciled_usd": 0.050079,  # unknown reserve worst-case (8 hung judges)
    "unreconciled_n": 8,
    "headroom_usd": 0.05,  # safety headroom (not a charge)
    "safe_ceiling_usd": 6.291941,
    "jsonl_rows": 3154,  # rows ≠ requests
    "request_ids": 3391,
    "ledger_commits": 3396,
    "orphans": 5,
    "agent_turns": 417,
    "prices_usd_per_mtok_as_of": "2026-11-08",
    "prices_usd_per_mtok": {"haiku": [1.0, 5.0], "sonnet": [3.0, 15.0]},
    "prices_kind": "list_price_assumption_at_study_date",
    "small_judge_per_call_usd": 0.001441445,  # measured NEW models.small.per_call
    "large_judge_per_call_usd": 0.00403281,
    "thinking_per_call_usd": 0.003397395,
    "month_small_judge_plus_reads_usd": 635.0,  # SIM volume × measured per-call (Ch16)
    "month_read_everything_usd": 7028.0,
    "order_not_decide": True,
}

# SIMULATED Harbor weekly release eval bill (product-line forecast), seeded.
# Unit economics anchored to Ch16 measured per-call where applicable.
SEED = 2041
WATERFALL = [
    {"name": "baseline_release_eval", "total_usd": 1900.0, "kind": "simulated_forecast"},
    {"name": "drop_unused_suites", "total_usd": 1520.0, "kind": "simulated_forecast"},
    {"name": "sample_by_risk", "total_usd": 1180.0, "kind": "simulated_forecast"},
    {"name": "cheap_first_cascade", "total_usd": 890.0, "kind": "simulated_forecast"},
    {"name": "cache_and_reuse", "total_usd": 740.0, "kind": "simulated_forecast"},
    {"name": "stop_when_settled", "total_usd": 640.0, "kind": "simulated_forecast"},
]

# Failure injection: cheaper judge clears TPR/TNR floors but fails bias battery
INJECT = {
    "label": "cheaper_judge_fails_bias_battery",
    "simulated": True,
    "cheap_tpr": 0.92,
    "cheap_tnr": 0.91,
    "position_flip_rate": 0.18,  # fails flip_ceiling 0.05
    "baseline_flip_rate": 0.02,
}


def digest(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def main():
    fix = {
        "seed": SEED,
        "ch16": CH16,
        "waterfall": WATERFALL,
        "inject": INJECT,
        "simulated_release_window": "SIMULATED Harbor weekly release eval bill, 2027-Q4 teaching window",
        "strata": [
            {"name": "hardship", "traffic_share": 0.059, "risk_weight": 40, "unit_cost_usd": 2.40},
            {"name": "fee", "traffic_share": 0.215, "risk_weight": 25, "unit_cost_usd": 0.90},
            {"name": "payoff_lien", "traffic_share": 0.168, "risk_weight": 20, "unit_cost_usd": 1.20},
            {"name": "account_statement", "traffic_share": 0.558, "risk_weight": 15, "unit_cost_usd": 0.35},
        ],
        "cascade_volumes": {
            "n_traces": 3514,
            "n_after_deterministic": 3200,
            "n_ordered_reads": 315,
        },
        "cascade_unit_costs": {
            "deterministic": 0.00002,
            "small_judge": CH16["small_judge_per_call_usd"],
            "human_read": 2.0,  # 2 min × $60/h
        },
    }
    fix["digest"] = digest({k: fix[k] for k in ("seed", "waterfall", "inject", "ch16")})
    (OUT / "fixture.json").write_text(json.dumps(fix, indent=2) + "\n")
    print("fixture", fix["digest"])


if __name__ == "__main__":
    main()
