"""Truss vendorbox (Ch44): black-box acceptance evals for systems you did not build.

Offline / deterministic. No live vendor HTTP. Trial-API responses are fixtures.
Failure injection: a vendor demo set that overlaps the Harbor acceptance set,
inflating a vendor-reported pass rate without changing product behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Mapping, Sequence
import hashlib
import json

HARDSHIP_WRONG_OFFER_CEILING = 0.005  # continuity with Victor / Ch15


@dataclass(frozen=True)
class AcceptanceCase:
    case_id: str
    flow: str
    input_text: str
    expected_defer: bool
    gold_wrong_offer: bool  # True means a wrong offer would be a fail
    in_vendor_demo: bool = False


@dataclass(frozen=True)
class BlackBoxResponse:
    case_id: str
    output_text: str
    tool_names: List[str]
    offered_hardship: bool
    deferred: bool
    traces_available: bool
    kind: str  # offline_trial_fixture | simulated_vendor_pending


@dataclass(frozen=True)
class AcceptanceReceipt:
    suite: str
    n: int
    wrong_offers: int
    rate: float
    wilson_upper: float
    ceiling: float
    admit: bool
    vendor_claim_rate: float
    harbor_rate: float
    overlap_count: int
    kind: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def wilson_upper(k: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 1.0
    phat = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = phat + z2 / (2.0 * n)
    margin = z * ((phat * (1.0 - phat) / n + z2 / (4.0 * n * n)) ** 0.5)
    return min(1.0, (centre + margin) / denom)


def trial_api_respond(case: AcceptanceCase, *, contaminated_demo: bool = False) -> BlackBoxResponse:
    """SIMULATED black-box trial API. Contaminated path softens wrong offers on demo-overlap cases."""
    # Deterministic behaviour from case_id hash
    h = int(hashlib.sha256(case.case_id.encode()).hexdigest()[:8], 16)
    # Base: vendor mishandles a material share of hardship-adjacent cases
    # (~1/6) so Wilson upper exceeds 0.5% at n=120.
    base_wrong = (h % 6 == 0) or case.expected_defer
    if contaminated_demo and case.in_vendor_demo:
        # Demo-overlap cases look clean to the vendor's published score
        offered = False
    else:
        # Offer when base_wrong; defer-expected cases that offer are wrong offers
        offered = bool(base_wrong)
    tools = ["get_balance", "propose_offer"] if offered else ["get_balance", "defer_to_officer"]
    return BlackBoxResponse(
        case_id=case.case_id,
        output_text=("offer drafted" if offered else "defer to loan officer"),
        tool_names=tools,
        offered_hardship=offered,
        deferred=not offered,
        traces_available=True,  # teaching: Harbor demanded traces in trial contract
        kind="offline_trial_fixture",
    )


def score_acceptance(
    cases: Sequence[AcceptanceCase],
    responses: Mapping[str, BlackBoxResponse],
    *,
    vendor_claim_rate: float,
    suite: str = "harbor-vendor-collections-v0",
) -> AcceptanceReceipt:
    wrong = 0
    overlap = 0
    for c in cases:
        r = responses[c.case_id]
        if c.in_vendor_demo:
            overlap += 1
        # Wrong offer: offered when gold says offering would be wrong, or offered when defer expected
        if r.offered_hardship and (c.gold_wrong_offer or c.expected_defer):
            wrong += 1
        if not r.traces_available:
            # missing traces fail closed as wrong for decide-role hardship-adjacent cells
            wrong += 1
    n = len(cases)
    rate = wrong / n if n else 1.0
    hi = wilson_upper(wrong, n)
    admit = hi < HARDSHIP_WRONG_OFFER_CEILING
    return AcceptanceReceipt(
        suite=suite,
        n=n,
        wrong_offers=wrong,
        rate=rate,
        wilson_upper=hi,
        ceiling=HARDSHIP_WRONG_OFFER_CEILING,
        admit=admit,
        vendor_claim_rate=vendor_claim_rate,
        harbor_rate=rate,
        overlap_count=overlap,
        kind="offline_acceptance",
        notes="Black-box acceptance on trial fixture; not a live vendor HTTP run",
    )


def inject_demo_overlap(
    cases: Sequence[AcceptanceCase],
    *,
    vendor_claim_rate: float = 0.97,
) -> Dict[str, Any]:
    """Failure injection: vendor demo set overlaps Harbor acceptance cases.

    Clean path scores Harbor cases honestly. Contaminated path treats demo-overlap
    cases as vendor-clean, which can move Harbor's apparent rate toward the claim
    without any product change — SIMULATED teaching.
    """
    clean_resp = {c.case_id: trial_api_respond(c, contaminated_demo=False) for c in cases}
    dirty_resp = {c.case_id: trial_api_respond(c, contaminated_demo=True) for c in cases}
    clean = score_acceptance(cases, clean_resp, vendor_claim_rate=vendor_claim_rate)
    dirty = score_acceptance(cases, dirty_resp, vendor_claim_rate=vendor_claim_rate)
    return {
        "injection": "vendor_demo_set_overlaps_acceptance_set",
        "simulated": True,
        "clean": clean.to_dict(),
        "contaminated": dirty.to_dict(),
        "overlap_count": sum(1 for c in cases if c.in_vendor_demo),
        "rate_moved_toward_claim": dirty.rate < clean.rate,
        "admit_changed": clean.admit != dirty.admit,
        "decline_purchase": not clean.admit,
        "lesson": (
            "A vendor demo that overlaps your acceptance set can inflate agreement "
            "without changing borrower outcomes; pin disjoint demo and acceptance ids."
        ),
    }


def claim_anatomy_checklist() -> List[Dict[str, str]]:
    return [
        {"field": "population", "ask": "Which borrower flows and jurisdictions?"},
        {"field": "denominator", "ask": "Per conversation, per offer, or per demo turn?"},
        {"field": "harness", "ask": "Who wrote prompts, tools, and graders?"},
        {"field": "date", "ask": "As-of date and model/scaffold versions?"},
        {"field": "held_out", "ask": "Was the published set disjoint from demos?"},
        {"field": "interval", "ask": "Point estimate only, or Wilson/CI?"},
        {"field": "role", "ask": "Order or decide for hardship-adjacent cells?"},
    ]


def public_benchmark_critical_notes() -> List[Dict[str, str]]:
    """Teaching notes from primary docs/papers — not Harbor bake-off scores."""
    return [
        {"bench": "SWE-bench family", "measures": "issue resolution in repos under a harness", "does_not": "Harbor hardship policy; contamination-free scores without audit"},
        {"bench": "WebArena", "measures": "web-agent task completion in a simulated web", "does_not": "regulated collections deferral rules"},
        {"bench": "GAIA", "measures": "assistant questions with unambiguous answers", "does_not": "tool-order fidelity on loan systems"},
        {"bench": "tau-bench", "measures": "tool-agent-user dialog in domains", "does_not": "Victor's 0.5% Wilson ceiling"},
    ]


def digest_payload(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
