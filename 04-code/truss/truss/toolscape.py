"""Truss toolscape (Ch43): platform adapters for a shared hardship-gate contract.

Offline / deterministic. Hosted platform SDKs are not called here.
Each adapt_* calls _pack → the SAME hardship_gate Wilson math; only the
`platform` string (and optional format envelope) differs. Format envelopes
are teaching-shaped JSON validated offline — not live SDK/HTTP/OTel output.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Mapping, Sequence
import hashlib
import json

PLATFORMS = (
    "langfuse",
    "phoenix",
    "braintrust",
    "langsmith",
    "promptfoo",
    "deepeval",
)

# Victor's hardship wrong-offer ceiling (error-rate upper bound), Ch15/Ch2 continuity.
HARDSHIP_WRONG_OFFER_CEILING = 0.005


@dataclass(frozen=True)
class GateReceipt:
    platform: str
    n: int
    wrong_offers: int
    rate: float
    wilson_upper: float
    ceiling: float
    admit: bool
    judge_version: str
    kind: str  # offline_adapter | simulated_hosted_pending
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def wilson_upper(k: int, n: int, z: float = 1.96) -> float:
    """Wilson score interval upper bound for a proportion."""
    if n <= 0:
        return 1.0
    phat = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = phat + z2 / (2.0 * n)
    margin = z * ((phat * (1.0 - phat) / n + z2 / (4.0 * n * n)) ** 0.5)
    return min(1.0, (centre + margin) / denom)


def hardship_gate(
    *,
    platform: str,
    n: int,
    wrong_offers: int,
    judge_version: str,
    ceiling: float = HARDSHIP_WRONG_OFFER_CEILING,
    kind: str = "offline_adapter",
    notes: str = "",
) -> GateReceipt:
    rate = (wrong_offers / n) if n else 1.0
    hi = wilson_upper(wrong_offers, n)
    admit = hi < ceiling
    return GateReceipt(
        platform=platform,
        n=n,
        wrong_offers=wrong_offers,
        rate=rate,
        wilson_upper=hi,
        ceiling=ceiling,
        admit=admit,
        judge_version=judge_version,
        kind=kind,
        notes=notes,
    )


# --- Offline adapters: same math, different packaging metadata ---

def _pack(platform: str, cases: Sequence[Mapping[str, Any]], judge_version: str) -> GateReceipt:
    n = len(cases)
    wrong = sum(1 for c in cases if c.get("wrong_offer"))
    return hardship_gate(
        platform=platform,
        n=n,
        wrong_offers=wrong,
        judge_version=judge_version,
        notes=f"{platform} offline adapter; scores pinned to judge_version={judge_version}",
    )


def adapt_langfuse(cases: Sequence[Mapping[str, Any]], judge_version: str) -> GateReceipt:
    """Langfuse: dataset run → experiment → LLM-as-judge / code scores on observations."""
    return _pack("langfuse", cases, judge_version)


def adapt_phoenix(cases: Sequence[Mapping[str, Any]], judge_version: str) -> GateReceipt:
    """Phoenix: OTel traces + dataset experiments + phoenix.evals judges."""
    return _pack("phoenix", cases, judge_version)


def adapt_braintrust(cases: Sequence[Mapping[str, Any]], judge_version: str) -> GateReceipt:
    """Braintrust: Eval/experiments + scorers; online scoring rules for production."""
    return _pack("braintrust", cases, judge_version)


def adapt_langsmith(cases: Sequence[Mapping[str, Any]], judge_version: str) -> GateReceipt:
    """LangSmith: offline datasets/experiments + online evaluators + annotation queues."""
    return _pack("langsmith", cases, judge_version)


def adapt_promptfoo(cases: Sequence[Mapping[str, Any]], judge_version: str) -> GateReceipt:
    """promptfoo: YAML asserts / llm-rubric in CI; redteam is a separate workflow."""
    return _pack("promptfoo", cases, judge_version)


def adapt_deepeval(cases: Sequence[Mapping[str, Any]], judge_version: str) -> GateReceipt:
    """DeepEval: pytest-style metrics (G-Eval etc.); optional Confident AI cloud."""
    return _pack("deepeval", cases, judge_version)



# --- Offline format envelopes (teaching shapes from primary docs; NOT SDK/HTTP output) ---
# Each envelope is a normalised contract fixture: serialize cases into a platform-shaped
# JSON document, validate required keys, then feed the SAME hardship_gate math.
# Hosted SDK calls remain PENDING.

ENVELOPE_REQUIRED = {
    "langfuse": ("dataset_name", "items", "experiment_name", "scores", "judge_version"),
    "phoenix": ("project", "spans", "dataset_version", "experiment_id", "evaluations", "judge_version"),
    "braintrust": ("project", "eval_name", "rows", "scorer_id", "judge_version"),
    "langsmith": ("dataset_id", "examples", "experiment_name", "runs", "judge_version"),
    "promptfoo": ("description", "providers", "tests", "defaultTest", "judge_version"),
    "deepeval": ("suite", "test_cases", "metrics", "judge_version"),
}


def build_format_envelope(
    platform: str,
    cases: Sequence[Mapping[str, Any]],
    judge_version: str,
) -> Dict[str, Any]:
    """Build an offline teaching envelope shaped like primary-doc artefacts.

    This is NOT a live export from a hosted product. It exists so readers can see
    which fields Truss would demand on a round-trip, and so tests can validate
    required keys before the shared hardship_gate runs.
    """
    if platform not in ENVELOPE_REQUIRED:
        raise ValueError(f"unknown platform {platform}")
    items = [
        {
            "id": c.get("id", f"case-{i}"),
            "input": c.get("input", {"flow": "hardship"}),
            "wrong_offer": bool(c.get("wrong_offer")),
            "metadata": {"flow": "hardship", "fixture": True},
        }
        for i, c in enumerate(cases)
    ]
    if platform == "langfuse":
        env = {
            "dataset_name": "harbor-hardship-gold",
            "items": items,
            "experiment_name": "hardship-gate-offline",
            "scores": [{"item_id": it["id"], "name": "wrong_offer", "value": 1.0 if it["wrong_offer"] else 0.0} for it in items],
            "judge_version": judge_version,
            "kind": "offline_format_envelope",
        }
    elif platform == "phoenix":
        env = {
            "project": "compass-staging",
            "spans": [{"trace_id": it["id"], "attributes": {"flow": "hardship", "wrong_offer": it["wrong_offer"]}} for it in items],
            "dataset_version": "hardship-v1",
            "experiment_id": "exp-offline-hardship",
            "evaluations": [{"span_id": it["id"], "score": 0.0 if not it["wrong_offer"] else 1.0} for it in items],
            "judge_version": judge_version,
            "kind": "offline_format_envelope",
        }
    elif platform == "braintrust":
        env = {
            "project": "harbor-eval",
            "eval_name": "hardship-wrong-offer",
            "rows": [{"input": it["input"], "scores": {"wrong_offer": it["wrong_offer"]}} for it in items],
            "scorer_id": "truss-hardship-scorer",
            "judge_version": judge_version,
            "kind": "offline_format_envelope",
        }
    elif platform == "langsmith":
        env = {
            "dataset_id": "ds-hardship-offline",
            "examples": [{"example_id": it["id"], "inputs": it["input"]} for it in items],
            "experiment_name": "hardship-offline",
            "runs": [{"example_id": it["id"], "outputs": {"wrong_offer": it["wrong_offer"]}} for it in items],
            "judge_version": judge_version,
            "kind": "offline_format_envelope",
        }
    elif platform == "promptfoo":
        env = {
            "description": "Harbor hardship offline asserts",
            "providers": ["truss:hardship-judge"],
            "tests": [{"vars": it["input"], "assert": [{"type": "javascript", "value": "output.wrong_offer === false"}]} for it in items],
            "defaultTest": {"metadata": {"flow": "hardship"}},
            "judge_version": judge_version,
            "kind": "offline_format_envelope",
        }
    else:  # deepeval
        env = {
            "suite": "hardship_gate",
            "test_cases": [{"input": str(it["input"]), "actual_output": "offer", "expected_output": "safe", "additional_metadata": {"wrong_offer": it["wrong_offer"]}} for it in items],
            "metrics": [{"name": "wrong_offer_rate", "threshold": HARDSHIP_WRONG_OFFER_CEILING}],
            "judge_version": judge_version,
            "kind": "offline_format_envelope",
        }
    return env


def validate_format_envelope(platform: str, envelope: Mapping[str, Any]) -> List[str]:
    """Return list of missing required keys; empty means OK."""
    req = ENVELOPE_REQUIRED[platform]
    return [k for k in req if k not in envelope]


def adapt_with_envelope(
    platform: str,
    cases: Sequence[Mapping[str, Any]],
    judge_version: str,
) -> Dict[str, Any]:
    """Serialize teaching envelope, validate keys, then run identical hardship_gate via _pack."""
    env = build_format_envelope(platform, cases, judge_version)
    missing = validate_format_envelope(platform, env)
    if missing:
        raise ValueError(f"{platform} envelope missing keys: {missing}")
    receipt = _pack(platform, cases, judge_version)
    return {"envelope": env, "missing": missing, "receipt": receipt}



ADAPTERS: Dict[str, Callable[[Sequence[Mapping[str, Any]], str], GateReceipt]] = {
    "langfuse": adapt_langfuse,
    "phoenix": adapt_phoenix,
    "braintrust": adapt_braintrust,
    "langsmith": adapt_langsmith,
    "promptfoo": adapt_promptfoo,
    "deepeval": adapt_deepeval,
}


def run_all_platforms(
    cases: Sequence[Mapping[str, Any]],
    judge_version: str,
) -> Dict[str, GateReceipt]:
    return {name: fn(cases, judge_version) for name, fn in ADAPTERS.items()}


def inject_judge_version_drift(
    cases: Sequence[Mapping[str, Any]],
    *,
    pinned_version: str,
    default_version: str,
    platform: str = "langsmith",
) -> Dict[str, Any]:
    """Failure injection: platform default re-scores with a different judge version.

    SIMULATED: the drifted scorer flips additional borderline cases to wrong_offer,
    so the Wilson upper can cross the ceiling even when the pinned judge would admit.
    """
    pinned = ADAPTERS[platform](cases, pinned_version)
    # SIMULATED drift: unpinned default flips a sparse subset of clean cases.
    # One flip is enough at n≈800 to push Wilson upper over the 0.5% ceiling.
    drifted_cases = []
    extra = 0
    for i, c in enumerate(cases):
        d = dict(c)
        if not d.get("wrong_offer") and (i == 0 or i % 40 == 0):
            d["wrong_offer"] = True
            d["drift_flip"] = True
            extra += 1
        drifted_cases.append(d)
    drifted = ADAPTERS[platform](drifted_cases, default_version)
    return {
        "injection": "platform_default_rescores_different_judge_version",
        "simulated": True,
        "platform": platform,
        "pinned": pinned.to_dict(),
        "drifted": drifted.to_dict(),
        "extra_wrong_offers": extra,
        "lesson": (
            "A platform default that re-scores with a different judge version can move "
            "the hardship gate without a product change; pin judge_version in Truss."
        ),
        "detect": pinned.judge_version != drifted.judge_version,
        "gate_changed": pinned.admit != drifted.admit,
    }


def capability_matrix() -> List[Dict[str, str]]:
    """Qualitative capability notes as of 2026-11-09 primary-doc research (not scores)."""
    # levels: strong / present / thin / n/a — teaching labels, not vendor rankings.
    return [
        {"platform": "langfuse", "traces": "strong", "datasets": "strong", "judges": "strong", "gates": "present", "reports": "strong", "residency": "self-host+cloud", "otel": "present"},
        {"platform": "phoenix", "traces": "strong", "datasets": "strong", "judges": "strong", "gates": "present", "reports": "strong", "residency": "self-host+cloud", "otel": "strong"},
        {"platform": "braintrust", "traces": "strong", "datasets": "strong", "judges": "strong", "gates": "present", "reports": "strong", "residency": "cloud-first", "otel": "present"},
        {"platform": "langsmith", "traces": "strong", "datasets": "strong", "judges": "strong", "gates": "present", "reports": "strong", "residency": "cloud+enterprise", "otel": "present"},
        {"platform": "promptfoo", "traces": "thin", "datasets": "present", "judges": "present", "gates": "strong", "reports": "present", "residency": "local+ci", "otel": "thin"},
        {"platform": "deepeval", "traces": "thin", "datasets": "present", "judges": "strong", "gates": "strong", "reports": "present", "residency": "local+optional-cloud", "otel": "thin"},
    ]


def recommendation_rows(as_of: str = "2026-11-09") -> List[Dict[str, str]]:
    return [
        {"context": "Regulated bank; self-host preference; OTel already in stack", "pick": "phoenix", "also": "langfuse", "avoid_as_sole": "cloud-only SaaS without residency controls", "as_of": as_of},
        {"context": "Product team already on LangChain; needs annotation queues", "pick": "langsmith", "also": "braintrust", "avoid_as_sole": "CI-only assert runner", "as_of": as_of},
        {"context": "CI-first PR gates + red-team scans; thin ops team", "pick": "promptfoo", "also": "deepeval", "avoid_as_sole": "hosted UI without export discipline", "as_of": as_of},
        {"context": "Pytest-native metrics library; custom G-Eval rubrics", "pick": "deepeval", "also": "promptfoo", "avoid_as_sole": "full observability replacement", "as_of": as_of},
        {"context": "Online scoring on production logs + experiment UX", "pick": "braintrust", "also": "langsmith", "avoid_as_sole": "local YAML-only workflow", "as_of": as_of},
        {"context": "Open-source default; datasets from production traces", "pick": "langfuse", "also": "phoenix", "avoid_as_sole": "vendor lock without OpenTelemetry export", "as_of": as_of},
    ]


def digest_payload(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
