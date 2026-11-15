"""Ch47 SIMULATED weekly sample + incident registry. Offline. seed=2047."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

SEED = 2047
N_WEEK = 70  # weekly stratified draw size (teaching)
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


def _tid(i: int) -> str:
    return f"t-{200000 + i:06d}"


def build(seed: int = SEED, n_week: int = N_WEEK):
    """Weekly sample of n_week traces + incident registry.
    One incident (bereavement-shaped teaching) has a trace_id that is NOT in the weekly sample —
    the failure injection for this chapter.
    """
    rng_ids = [_tid(i) for i in range(1, n_week + 1)]
    # Incident that was never sampled: outside the weekly id range
    missed_incident_tid = "t-199847"
    incidents = [
        {
            "incident_id": "inc-2047-01",
            "opened": "2027-06-12",
            "channel": "complaint",
            "summary": "EXAMPLE (hypothetical): borrower alleged hardship offer refused after bereavement disclosure",
            "linked_trace_id": missed_incident_tid,
            "in_weekly_sample": False,
            "severity_set": True,
        },
        {
            "incident_id": "inc-2047-02",
            "opened": "2027-06-10",
            "channel": "officer",
            "summary": "EXAMPLE: fee explanation disputed; already in weekly sample",
            "linked_trace_id": rng_ids[12],
            "in_weekly_sample": True,
            "progression_set": False,
        },
    ]
    rows = []
    for i, tid in enumerate(rng_ids):
        flow = ["account", "fee", "hardship", "payoff", "lien", "statement"][i % 6]
        rows.append({"trace_id": tid, "flow": flow, "week": "2027-W24", "sampled": True})
    sample_ids = {r["trace_id"] for r in rows}
    assert missed_incident_tid not in sample_ids
    assert incidents[0]["linked_trace_id"] not in sample_ids
    assert incidents[1]["linked_trace_id"] in sample_ids

    payload = {
        "seed": seed,
        "n_week": n_week,
        "SIMULATED": True,
        "label": "ch47_incident_to_eval_weekly_sample",
        "rows": rows,
        "incidents": incidents,
        "missed_incident_trace_id": missed_incident_tid,
        "traffic_share_teaching": 1.0,  # chapter climax: 100% after Victor signs (teaching scenario)
        "prior_traffic_share": 0.10,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    payload["digest"] = digest
    (OUT / "fixture.json").write_text(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    p = build()
    print(f"digest={p['digest']} n_week={p['n_week']} missed={p['missed_incident_trace_id']}")
