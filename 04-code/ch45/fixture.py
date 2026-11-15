"""Ch45 SIMULATED hardship segment fixture. Offline. seed=2045. n=2400."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

SEED = 2045
N = 2400
OUT = Path(__file__).parent / "out"

CHANNELS = ["web", "phone", "branch"]
PRODUCTS = ["signature", "compass"]
# Legitimate strata: channel × product = 6 segments
# Pre-remediation wrong-offer Bernoulli-ish via deterministic hash so reproducible


def _bit(trace_id: str, salt: str, threshold: float) -> int:
    h = hashlib.sha256(f"{salt}:{trace_id}".encode()).hexdigest()
    # map first 8 hex to [0,1)
    u = int(h[:8], 16) / 0xFFFFFFFF
    return 1 if u < threshold else 0


def _name_proxy(trace_id: str) -> str:
    """Synthetic name-coded affinity bucket — NOT a legitimate business segment.
    Teaching failure injection: treating this as a 'segment' is itself a protected-characteristic proxy.
    """
    h = int(hashlib.sha256(f"nameproxy:{trace_id}".encode()).hexdigest()[:8], 16)
    return "affinity_A" if (h % 2 == 0) else "affinity_B"


def build(seed: int = SEED, n: int = N):
    # Pre-remediation per-segment wrong rates (teaching): phone×signature hot
    pre_rates = {
        ("web", "signature"): 0.0035,
        ("web", "compass"): 0.0030,
        ("phone", "signature"): 0.0140,  # gap
        ("phone", "compass"): 0.0040,
        ("branch", "signature"): 0.0038,
        ("branch", "compass"): 0.0032,
    }
    # Post-remediation: phone×signature brought down without inflating others
    post_rates = dict(pre_rates)
    post_rates[("phone", "signature")] = 0.0042

    rows = []
    # balanced-ish assignment across 6 strata
    strata = list(pre_rates)
    for i in range(n):
        ch, prod = strata[i % 6]
        tid = f"H{seed}-{i:04d}"
        pre = _bit(tid, "pre", pre_rates[(ch, prod)])
        post = _bit(tid, "post", post_rates[(ch, prod)])
        # For phone×signature, force enough fails in pre to make Wilson hi clearly over 0.5%
        # and fewer in post — calibrated below after first build if needed
        rows.append({
            "trace_id": tid,
            "channel": ch,
            "product": prod,
            "segment": f"{ch}×{prod}",
            "wrong_offer_pre": pre,
            "wrong_offer_post": post,
            "affinity_bucket": _name_proxy(tid),  # illegal proxy if used as decide segment
        })

    # Calibrate phone×signature pre fails to ~14/400 = 3.5% if hash under-fires
    # Ensure teaching numbers: overall pre near Ch31-ish; segment gap clear
    def _force_segment(rows, seg, field, k_target):
        idxs = [i for i, r in enumerate(rows) if r["segment"] == seg]
        # clear then set first k
        for i in idxs:
            rows[i][field] = 0
        for i in idxs[:k_target]:
            rows[i][field] = 1

    # Each stratum ~400 rows
    _force_segment(rows, "phone×signature", "wrong_offer_pre", 14)   # 14/400=3.5%
    _force_segment(rows, "phone×signature", "wrong_offer_post", 3)    # 3/400=0.75% still elevated but remediating
    _force_segment(rows, "web×signature", "wrong_offer_pre", 2)
    _force_segment(rows, "web×signature", "wrong_offer_post", 2)
    _force_segment(rows, "web×compass", "wrong_offer_pre", 2)
    _force_segment(rows, "web×compass", "wrong_offer_post", 2)
    _force_segment(rows, "phone×compass", "wrong_offer_pre", 2)
    _force_segment(rows, "phone×compass", "wrong_offer_post", 2)
    _force_segment(rows, "branch×signature", "wrong_offer_pre", 2)
    _force_segment(rows, "branch×signature", "wrong_offer_post", 2)
    _force_segment(rows, "branch×compass", "wrong_offer_pre", 1)
    _force_segment(rows, "branch×compass", "wrong_offer_post", 1)
    # post remediation also gently reduce phone×signature further in narrative: 2 fails
    _force_segment(rows, "phone×signature", "wrong_offer_post", 2)

    blob = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(blob).hexdigest()[:12]
    return {
        "seed": seed,
        "n": n,
        "SIMULATED": True,
        "digest": digest,
        "target_wrong_offer": 0.005,
        "rows": rows,
        "legitimate_segments": [f"{c}×{p}" for c, p in strata],
        "illegal_proxy_field": "affinity_bucket",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fix = build()
    (OUT / "fixture.json").write_text(json.dumps(fix, indent=2))
    print(f"digest={fix['digest']} n={fix['n']} SIMULATED seed={fix['seed']}")


if __name__ == "__main__":
    main()
