"""Ch46 fixture: validation-pack teaching freeze refs (SIMULATED). No paid calls."""
from __future__ import annotations
import json, hashlib
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

SEED = 2046
# Continuity refs from accepted Ch45 teaching (by digest reference; do not mutate Ch45 files)
CH45_DIGEST = "af63808723f1"
CH45_RECORD = "3d4c15e44e50"
N = 2400
PRE_K, POST_K = 23, 11
HOT_PRE_K, HOT_POST_K, HOT_N = 14, 2, 400
TARGET = 0.005

# Canonical metric definition in the pack (authoritative)
PACK_METRIC = {
    "metric_id": "wrong_hardship_offer_rate",
    "definition": "binary wrong-offer under pinned gold on frozen hardship offers; Wilson 95% upper vs 0.5%",
    "unit": "offer",
    "denominator": "frozen hardship offers in digest population",
    "gold_digest": CH45_DIGEST,
    "version": "v1-pack",
}

# Drifted dashboard definition (failure injection target)
DASHBOARD_METRIC_DRIFT = {
    "metric_id": "wrong_hardship_offer_rate",
    "definition": "binary wrong-offer under pinned gold on frozen hardship conversations; Wilson 95% upper vs 0.5%",
    "unit": "conversation",  # DRIFT: unit changed
    "denominator": "hardship conversations in last 30 days (rolling)",  # DRIFT: population
    "gold_digest": CH45_DIGEST,
    "version": "v1-dashboard-drift",
}


def main():
    payload = {
        "seed": SEED,
        "simulated": True,
        "kind": "SIMULATED",
        "ch45_digest_ref": CH45_DIGEST,
        "ch45_record_ref": CH45_RECORD,
        "n": N,
        "target": TARGET,
        "pre_overall": {"k": PRE_K, "n": N},
        "post_overall": {"k": POST_K, "n": N},
        "hot_segment": {
            "name": "phone×signature",
            "pre_k": HOT_PRE_K,
            "post_k": HOT_POST_K,
            "n": HOT_N,
        },
        "pack_metric": PACK_METRIC,
        "dashboard_metric_drift": DASHBOARD_METRIC_DRIFT,
        "owners": {
            "ship": "Victor Lane",
            "eval_lead": "evaluation lead",
            "product": "product",
            "counsel_challenge": "counsel",
        },
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["fixture_sha12"] = hashlib.sha256(raw).hexdigest()[:12]
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2) + "\n")
    print("fixture", payload["fixture_sha12"])


if __name__ == "__main__":
    main()
