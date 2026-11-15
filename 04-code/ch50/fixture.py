"""Ch50 fixture: Truss-like eval configs for the catalogue linter."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
SEED = 2050


def build():
    configs = {
        "harbor_compass_v3": {
            "name": "harbor_compass_v3",
            "suite_digest": "a1b2c3d4e5f6",
            "population": "hardship_offers_10pct_arm",
            "metric": "wrong_offer_rate",
            "bound": 0.005,
            "judge": {
                "id": "fee_span_judge_v2",
                "validated": True,
                "gold_n": 120,
                "agreement_beyond_chance": True,
                "bias_probe": True,
            },
            "gate": {"kind": "release", "fail_closed": True, "requires_validated_judge": True},
            "owner": "eval_lead",
            "SIMULATED": True,
        },
        "linter_pass_unvalidated_judge": {
            "name": "linter_pass_unvalidated_judge",
            "suite_digest": "f6e5d4c3b2a1",
            "population": "account_question_flows",
            "metric": "faithfulness_proxy",
            "bound": 0.02,
            "judge": {
                "id": "vendor_score_judge_v0",
                "validated": False,
                "gold_n": 0,
                "agreement_beyond_chance": False,
                "bias_probe": False,
            },
            "gate": {"kind": "release", "fail_closed": True, "requires_validated_judge": True},
            "owner": "eval_lead",
            "SIMULATED": True,
            "FAILURE_INJECTION": True,
        },
        "missing_population": {
            "name": "missing_population",
            "suite_digest": "112233445566",
            "population": "",
            "metric": "accuracy",
            "bound": 0.01,
            "judge": {
                "id": "ok_judge",
                "validated": True,
                "gold_n": 80,
                "agreement_beyond_chance": True,
                "bias_probe": True,
            },
            "gate": {"kind": "release", "fail_closed": True, "requires_validated_judge": True},
            "owner": "eval_lead",
            "SIMULATED": True,
        },
    }
    raw = json.dumps({"seed": SEED, "configs": configs}, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    payload = {
        "seed": SEED,
        "digest": digest,
        "n_configs": len(configs),
        "configs": configs,
        "SIMULATED": True,
        "live_provider_eval_sweeps": "PENDING",
        "paid_calls": False,
    }
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"digest": digest, "seed": SEED, "n": len(configs)}))


if __name__ == "__main__":
    build()
