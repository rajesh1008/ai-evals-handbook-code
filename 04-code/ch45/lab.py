"""Ch45 lab: segment fairness cards + evidence pack. Offline SIM."""
from __future__ import annotations
import json, sys, hashlib
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.rates import wilson, upper_bound

OUT = Path(__file__).parent / "out"
TARGET = 0.005


def segment_card(rows, field: str, segment_key: str):
    buckets = defaultdict(list)
    for r in rows:
        buckets[r[segment_key]].append(r[field])
    cards = []
    for seg, ys in sorted(buckets.items()):
        k = sum(ys)
        n = len(ys)
        lo, hi = wilson(k, n)
        cards.append({
            "segment": seg,
            "k": k,
            "n": n,
            "rate": k / n if n else float("nan"),
            "wilson_lo": lo,
            "wilson_hi": hi,
            "clopper_upper_approx": upper_bound(k, n),
            "meets_upper_bound_target": bool(hi < TARGET) if n else False,
            "OPEN": bool(hi >= TARGET) if n else True,
        })
    return cards


def overall(rows, field: str):
    ys = [r[field] for r in rows]
    k = sum(ys)
    n = len(ys)
    lo, hi = wilson(k, n)
    return {
        "k": k, "n": n, "rate": k / n,
        "wilson_lo": lo, "wilson_hi": hi,
        "meets": hi < TARGET, "OPEN": hi >= TARGET,
    }


def adverse_ratio(cards, baseline_seg: str):
    """Simple adverse-outcome ratio vs a named baseline segment (teaching)."""
    by = {c["segment"]: c for c in cards}
    base = by[baseline_seg]["rate"]
    out = []
    for c in cards:
        ratio = (c["rate"] / base) if base > 0 else float("nan")
        out.append({"segment": c["segment"], "rate": c["rate"], "ratio_vs_baseline": ratio,
                    "baseline": baseline_seg})
    return out


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    rows = fix["rows"]
    pre_seg = segment_card(rows, "wrong_offer_pre", "segment")
    post_seg = segment_card(rows, "wrong_offer_post", "segment")
    pre_ov = overall(rows, "wrong_offer_pre")
    post_ov = overall(rows, "wrong_offer_post")

    # Gap: largest wilson_hi among legitimate segments pre
    hot = max(pre_seg, key=lambda c: c["wilson_hi"])
    remediated = next(c for c in post_seg if c["segment"] == hot["segment"])

    # Illegal proxy analysis (must not be a decide card)
    proxy_pre = segment_card(rows, "wrong_offer_pre", "affinity_bucket")
    proxy_spread = max(c["rate"] for c in proxy_pre) - min(c["rate"] for c in proxy_pre)

    ratios = adverse_ratio(pre_seg, baseline_seg="web×compass")

    evidence_pack = {
        "control_objective": "wrong_hardship_offer_rate upper bound under 0.5%",
        "population": "hardship_offer_traces",
        "n": fix["n"],
        "digest": fix["digest"],
        "metric": "wrong_offer",
        "target": TARGET,
        "legitimate_strata": fix["legitimate_segments"],
        "pre_overall": pre_ov,
        "post_overall": post_ov,
        "pre_segments": pre_seg,
        "post_segments": post_seg,
        "hot_segment_pre": hot,
        "hot_segment_post": remediated,
        "adverse_ratios_pre": ratios,
        "owner": "Victor",
        "SIMULATED": True,
    }

    rec = {
        "experiment_id": "ch45-hardship-segment-fairness",
        "digest": fix["digest"],
        "seed": fix["seed"],
        "n": fix["n"],
        "hypothesis": "legitimate channel×product strata; affinity_bucket is illegal proxy",
        "owner": "Victor",
    }
    rec_sha = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()[:12]
    rec["record_sha12"] = rec_sha

    lab = {
        "evidence_pack": evidence_pack,
        "record": rec,
        "proxy_injection": {
            "field": "affinity_bucket",
            "caught": True,
            "reason": "name-coded affinity bucket is a protected-characteristic proxy, not a business stratum",
            "cards_must_not_decide": proxy_pre,
            "rate_spread": proxy_spread,
        },
        "target": TARGET,
        "SIMULATED": True,
    }
    (OUT / "lab.json").write_text(json.dumps(lab, indent=2))
    print(json.dumps({
        "digest": fix["digest"],
        "record_sha12": rec_sha,
        "pre_overall": pre_ov,
        "post_overall": post_ov,
        "hot": hot["segment"],
        "hot_pre_hi": hot["wilson_hi"],
        "hot_post_hi": remediated["wilson_hi"],
        "proxy_caught": True,
    }, indent=2))


if __name__ == "__main__":
    main()
