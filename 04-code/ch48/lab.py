"""Ch48 lab: score trace reviews with findings rubric vs vocabulary rubric."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"

PLANTED = {
    "t-48001": "offer_before_income",
    "t-48002": "grace_period_misquote",
    "t-48004": "missing_officer_handoff",
    "t-48005": "per_diem_omitted",
    "t-48007": "wrong_period",
}
S1 = {"t-48001", "t-48004"}


def score_findings(review: dict) -> dict:
    notes = {n["trace_id"]: n["finding"] for n in review["notes"]}
    hits = sum(1 for tid, f in PLANTED.items() if notes.get(tid) == f)
    s1_hits = sum(1 for tid in S1 if notes.get(tid) == PLANTED[tid])
    false_alarms = sum(1 for tid, f in notes.items() if tid not in PLANTED or PLANTED.get(tid) != f)
    # Weight S1 heavily
    score = 10 * s1_hits + 4 * (hits - s1_hits) - 2 * false_alarms
    return {
        "rubric": "findings",
        "hits": hits,
        "s1_hits": s1_hits,
        "false_alarms": false_alarms,
        "score": score,
        "rank_key": score,
    }


def score_vocabulary(review: dict) -> dict:
    """FAILURE INJECTION: rewards buzzword density over planted findings."""
    vocab = review.get("vocab_hits") or []
    # Inflate by vocabulary count; ignore whether findings match gold
    score = 3 * len(vocab) + len(review["notes"])
    return {
        "rubric": "vocabulary_reward",
        "vocab_count": len(vocab),
        "notes_count": len(review["notes"]),
        "score": score,
        "rank_key": score,
        "FAILURE_INJECTION": True,
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    rows = []
    for key, rev in fix["reviews"].items():
        fr = score_findings(rev)
        vr = score_vocabulary(rev)
        rows.append({
            "review_key": key,
            "candidate": rev["candidate"],
            "findings": fr,
            "vocabulary": vr,
        })
    # Rankings
    by_findings = sorted(rows, key=lambda r: r["findings"]["score"], reverse=True)
    by_vocab = sorted(rows, key=lambda r: r["vocabulary"]["score"], reverse=True)
    evidence = {
        "control_objective": "hiring loop scores trace-review findings; vocabulary-reward rubrics must be caught as failure injections",
        "digest": fix["digest"],
        "seed": fix["seed"],
        "n_traces": fix["n_traces"],
        "rows": rows,
        "rank_findings": [r["candidate"] for r in by_findings],
        "rank_vocabulary": [r["candidate"] for r in by_vocab],
        "inversion": by_findings[0]["candidate"] != by_vocab[0]["candidate"],
        "winner_findings": by_findings[0]["candidate"],
        "winner_vocabulary": by_vocab[0]["candidate"],
        "SIMULATED": True,
        "live_provider_eval_sweeps": "PENDING",
        "paid_calls": False,
    }
    raw = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    record = {"record_sha12": hashlib.sha256(raw).hexdigest()[:12], "experiment_id": "ch48-hiring-trace-review"}
    payload = {"SIMULATED": True, "evidence_pack": evidence, "record": record, "digest": fix["digest"]}
    (OUT / "lab.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({
        "digest": fix["digest"],
        "record": record["record_sha12"],
        "winner_findings": evidence["winner_findings"],
        "winner_vocabulary": evidence["winner_vocabulary"],
        "inversion": evidence["inversion"],
    }, indent=2))


if __name__ == "__main__":
    main()
