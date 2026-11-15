"""Failure injection: easy-first queue ordering hides fatigue effect."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.reviewer import fatigue_curve, agreement_with_gold

OUT = Path(__file__).parent / "out"

def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    rows = list(fix["rows"])
    # Natural order fatigue (by original queue_position)
    natural = fatigue_curve(rows, bins=5)
    # Easy-first: put agreements / short times early, hard/wrong plants late
    easy_first = sorted(rows, key=lambda r: (0 if (r["human_label"] == r["gold"] and not r["ai_wrong"]) else 1, r["approval_seconds"]))
    for i, r in enumerate(easy_first):
        r = dict(r)
        r["queue_position"] = i + 1
        easy_first[i] = r
    # If we only look at first 40% of easy-first queue, fatigue looks flat/high
    head = easy_first[: int(0.4 * len(easy_first))]
    tail = easy_first[int(0.6 * len(easy_first)) :]
    out = {
        "lesson": "Easy-first queue ordering hides fatigue: early window looks fine while late window collapses.",
        "natural_fatigue": natural,
        "easy_first_head_agreement": agreement_with_gold(head)["agreement"],
        "easy_first_tail_agreement": agreement_with_gold(tail)["agreement"],
        "easy_first_curve": fatigue_curve(easy_first, bins=5),
        "named": "queue-order-injection",
        "simulated": True,
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(out)

if __name__ == "__main__":
    main()
