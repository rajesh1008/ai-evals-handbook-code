"""Ch48 SIMULATED trace-review pack for hiring. Offline. seed=2048."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

SEED = 2048
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# Eight teaching traces (paraphrased shapes; not production exports)
TRACES = [
    {"trace_id": "t-48001", "flow": "hardship", "turns": 7, "planted_finding": "offer_before_income", "gold_severity": "S1"},
    {"trace_id": "t-48002", "flow": "fee_explanation", "turns": 4, "planted_finding": "grace_period_misquote", "gold_severity": "S2"},
    {"trace_id": "t-48003", "flow": "account_question", "turns": 3, "planted_finding": None, "gold_severity": "ok"},
    {"trace_id": "t-48004", "flow": "hardship", "turns": 9, "planted_finding": "missing_officer_handoff", "gold_severity": "S1"},
    {"trace_id": "t-48005", "flow": "payoff_letter", "turns": 5, "planted_finding": "per_diem_omitted", "gold_severity": "S2"},
    {"trace_id": "t-48006", "flow": "lien_release", "turns": 4, "planted_finding": None, "gold_severity": "ok"},
    {"trace_id": "t-48007", "flow": "statement_request", "turns": 2, "planted_finding": "wrong_period", "gold_severity": "S3"},
    {"trace_id": "t-48008", "flow": "fee_explanation", "turns": 6, "planted_finding": None, "gold_severity": "ok"},
]

# Two candidate reviews of the pack (SIMULATED teaching artefacts)
REVIEWS = {
    "findings_first": {
        "candidate": "A",
        "notes": [
            {"trace_id": "t-48001", "finding": "offer_before_income", "evidence": "tool income unset; offer drafted turn 4"},
            {"trace_id": "t-48002", "finding": "grace_period_misquote", "evidence": "ten-day grace stated; schedule is five"},
            {"trace_id": "t-48004", "finding": "missing_officer_handoff", "evidence": "borrower asked for person; no escalate span"},
            {"trace_id": "t-48005", "finding": "per_diem_omitted", "evidence": "payoff quote lacks per-diem line"},
            {"trace_id": "t-48007", "finding": "wrong_period", "evidence": "statement window off by one month"},
        ],
        "vocab_hits": ["trace", "gate", "interval"],
        "missed_s1": 0,
        "false_alarms": 0,
    },
    "vocabulary_heavy": {
        "candidate": "B",
        "notes": [
            {"trace_id": "t-48001", "finding": "needs_better_rag", "evidence": "LLM-as-judge would catch drift with golden sets"},
            {"trace_id": "t-48002", "finding": "observability_gap", "evidence": "need agentic eval harness and red-team suite"},
            {"trace_id": "t-48003", "finding": "prompt_sensitivity", "evidence": "should add offline/online pipelines"},
            {"trace_id": "t-48006", "finding": "hallucination_risk", "evidence": "recommend rubric calibration and CI gates"},
            {"trace_id": "t-48008", "finding": "tool_use_correctness", "evidence": "faithfulness groundedness relevance dashboard"},
        ],
        "vocab_hits": [
            "LLM-as-judge", "golden sets", "drift", "observability", "agentic", "red-team",
            "offline", "online", "pipelines", "hallucination", "rubric", "calibration",
            "CI", "gates", "faithfulness", "groundedness", "relevance", "dashboard",
        ],
        "missed_s1": 2,  # missed both S1 planted findings with correct labels
        "false_alarms": 3,
    },
}


def build(seed: int = SEED):
    payload = {
        "seed": seed,
        "SIMULATED": True,
        "label": "ch48_trace_review_hiring_pack",
        "n_traces": len(TRACES),
        "traces": TRACES,
        "reviews": REVIEWS,
        "harbor_second_hire": True,
        "live_provider_eval_sweeps": "PENDING",
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    payload["digest"] = digest
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    p = build()
    print(f"digest={p['digest']} n={p['n_traces']}")
