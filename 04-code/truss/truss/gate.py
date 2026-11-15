"""Chapter 2: Gate v0. Paired comparison of a candidate against the baseline
on the same traces, plus the rules nobody may override."""
from scipy.stats import binomtest


def paired_changes(base, cand):
    """Per flow: traces that went pass->fail (b) and fail->pass (c)."""
    out = {}
    for t, (flow, v0) in base.items():
        v1 = cand[t][1]
        b, c = out.get(flow, (0, 0))
        out[flow] = (b + (v0 == "pass" and v1 == "fail"), c + (v0 == "fail" and v1 == "pass"))
    return out


def decide(manifest_ok, incomplete, changes, new_wrong_offers, alpha=0.05):
    reasons = []
    if not manifest_ok:
        reasons.append("manifest does not match the candidate")
    if incomplete:
        reasons.append(f"{incomplete} replayed traces fail the completeness check")
    if new_wrong_offers:
        reasons.append(f"{new_wrong_offers} new wrong hardship offers")
    for flow, (b, c) in sorted(changes.items()):
        if flow == "hardship" and b:
            reasons.append(f"hardship: {b} traces newly fail (loan officer review required)")
        elif b + c and binomtest(b, b + c, 0.5, alternative="greater").pvalue < alpha:
            reasons.append(f"{flow}: {b} newly fail, {c} newly pass (paired p < {alpha})")
    return ("hold" if reasons else "ship"), reasons
