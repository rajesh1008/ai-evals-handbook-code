"""Ch46 lab: build eight-artefact validation pack + second-person table reproduce."""
from __future__ import annotations
import json, hashlib, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.rates import wilson

OUT = Path(__file__).parent / "out"

EIGHT = [
    "A1_use_case_inventory",
    "A2_conceptual_soundness",
    "A3_metric_digest_register",
    "A4_outcome_analysis",
    "A5_reproducibility_recipe",
    "A6_monitoring_plan",
    "A7_limitations_pending_scope",
    "A8_challenge_log",
]


def card(k, n, target=0.005):
    lo, hi = wilson(k, n)
    return {
        "k": k,
        "n": n,
        "rate": k / n,
        "wilson_lo": lo,
        "wilson_hi": hi,
        "OPEN": hi >= target,
        "meets_upper_bound_target": hi < target,
        "interval_kind": "ordinary_wilson_95_approximate_finite_sample",
        "design_note": "SIM teaching; not an exact level-alpha certificate",
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    pre = card(fix["pre_overall"]["k"], fix["pre_overall"]["n"], fix["target"])
    post = card(fix["post_overall"]["k"], fix["post_overall"]["n"], fix["target"])
    hot_pre = card(fix["hot_segment"]["pre_k"], fix["hot_segment"]["n"], fix["target"])
    hot_post = card(fix["hot_segment"]["post_k"], fix["hot_segment"]["n"], fix["target"])

    # Table the second person must reproduce (machine authority)
    reproduce_table = {
        "table_id": "hardship_overall_pre_post",
        "rows": [
            {"label": "pre_overall", **pre},
            {"label": "post_overall", **post},
            {"label": "hot_pre", "segment": fix["hot_segment"]["name"], **hot_pre},
            {"label": "hot_post", "segment": fix["hot_segment"]["name"], **hot_post},
        ],
    }
    table_bytes = json.dumps(reproduce_table, sort_keys=True, separators=(",", ":")).encode()
    table_sha12 = hashlib.sha256(table_bytes).hexdigest()[:12]

    pack = {
        "kind": "SIMULATED",
        "seed": fix["seed"],
        "pack_id": "harbor-hardship-validation-pack-teaching",
        "artefacts": {
            "A1_use_case_inventory": {
                "system": "Compass hardship-offer assistance",
                "population": "frozen hardship offers",
                "n": fix["n"],
                "business_use": "draft hardship offers; human ship verb retained",
                "inventory_status": "candidate_for_model_inventory_discussion",
                "sr26_2_scope_note": "Generative and agentic AI are outside SR 26-2 scope per interagency guidance 17 Apr 2026; pack still uses MRM vocabulary as translation without claiming in-scope model status.",
            },
            "A2_conceptual_soundness": {
                "unit_of_analysis": "offer",
                "assumptions": [
                    "pinned gold and policy digests before scoring",
                    "ordinary Wilson intervals are approximate finite-sample diagnostics",
                    "SIM independence assumption for teaching cards; production may need cluster-aware methods",
                ],
                "design_choices": ["channel×product strata pre-declared", "proxy fields refused as decide inputs"],
            },
            "A3_metric_digest_register": {
                "pack_metric": fix["pack_metric"],
                "gold_digest": fix["ch45_digest_ref"],
                "record_sha12": fix["ch45_record_ref"],
                "target": fix["target"],
            },
            "A4_outcome_analysis": {
                "source": "Ch45 teaching freeze by digest reference",
                "overall_pre": pre,
                "overall_post": post,
                "hot_segment": fix["hot_segment"]["name"],
                "hot_pre": hot_pre,
                "hot_post": hot_post,
                "ship_language": "OPEN; residual risk only with Victor signature — not MEETS",
            },
            "A5_reproducibility_recipe": {
                "input": ["tag ch46-validation-pack-teaching", f"digest {fix['ch45_digest_ref']}", f"record {fix['ch45_record_ref']}"],
                "command": "./run_all.sh",
                "output_must_include": ["SIMULATED", "table_sha12", "metric_drift_caught"],
                "second_person_table_sha12": table_sha12,
            },
            "A6_monitoring_plan": {
                "weekly_segment_cards": True,
                "stop_rules": "Wilson hi or count budget; under-powered weeks labelled",
                "retest_triggers": [
                    "provider model bump",
                    "prompt change",
                    "policy change",
                    "mix shock",
                    "hardship incident",
                    "quarterly calendar",
                ],
            },
            "A7_limitations_pending_scope": {
                "live_provider_batteries": "PENDING",
                "name_swap_counterfactual": "PENDING",
                "paid_calls_this_chapter": False,
                "sr26_2_generative_agentic_excluded": True,
                "wilson_exact_iut_guarantee": False,
            },
            "A8_challenge_log": {
                "challenges": [
                    {"id": "C1", "probe": "metric unit offer vs conversation", "result": "pack unit=offer"},
                    {"id": "C2", "probe": "MEETS while Wilson OPEN", "result": "refused"},
                    {"id": "C3", "probe": "benchmark score as validation", "result": "refused"},
                    {"id": "C4", "probe": "author marks own homework", "result": "challenger required"},
                ],
                "independence": "effective challenge by non-author role before committee",
            },
        },
        "artefact_order": EIGHT,
        "reproduce_table": reproduce_table,
        "table_sha12": table_sha12,
        "owners": fix["owners"],
        "returned_artefact": {
            "id": "A4_outcome_analysis",
            "reason": "validator requests borrower-level sensitivity note beside offer-level Wilson cards",
            "status": "returned_for_more_evidence",
            "remediation_design": "add DESIGN borrower-level sensitivity appendix; do not invent borrower k/n for teaching digest",
        },
    }
    raw = json.dumps(pack, sort_keys=True, separators=(",", ":")).encode()
    pack["pack_sha12"] = hashlib.sha256(raw).hexdigest()[:12]
    (OUT / "lab.json").write_text(json.dumps(pack, indent=2) + "\n")
    (OUT / "reproduce_table.json").write_text(json.dumps(reproduce_table, indent=2) + "\n")
    print("pack", pack["pack_sha12"], "table", table_sha12)


if __name__ == "__main__":
    main()
