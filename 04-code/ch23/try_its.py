"""Three Try-it-yourself variations for Chapter 23."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from truss.retrieval import RetrievalGold, evaluate_rankings, filter_synthetic, groundedness_rate
from corpus import corpus_tokens, live_chunk_ids
from fixture import build_gold, grounding_rows, rankings_for_index, RANK_SEED


def main():
    gold_rows = build_gold(90)
    gold = [
        RetrievalGold(g["query_id"], g["query"], frozenset(g["relevant"]), g["source_digest"], dict(g["graded"]))
        for g in gold_rows
    ]
    live = live_chunk_ids()
    rank = rankings_for_index(gold_rows, live, noise=0.40, seed=RANK_SEED)

    print("Try It 1: change k from 5 to 1 and to 10")
    for k in (1, 5, 10):
        rep = evaluate_rankings(gold, rank, k=k)
        print(f"  k={k}: recall={rep['recall_at_k']:.3f} hit={rep['hit_at_k']:.3f} MRR={rep['mrr']:.3f}")

    print("Try It 2: raise groundedness overlap floor from 0.35 to 0.55")
    rows = grounding_rows(gold_rows, rank, k=5)
    for floor in (0.35, 0.55):
        g = groundedness_rate(rows, min_overlap=floor)
        print(f"  floor={floor}: {g['supported']}/{g['n']} rate={g['rate']:.3f}")

    print("Try It 3: synthetic filter without the unanswerable rule (keep short only)")
    synth = [
        {"query": "late fee grace period days"},
        {"query": "hi"},
        {"query": "quantum banana orchard zodiac"},
        {"query": "hardship twelve month window"},
    ]
    # manual: only drop too_short / duplicate using filter_synthetic as-is, then compare
    full = filter_synthetic(synth, corpus_tokens())
    print(f"  full filter kept={len(full['kept'])} reasons={full['reasons']}")
    # weaken: treat corpus as all tokens from queries themselves (everything 'answerable')
    weak = filter_synthetic(synth, set(w for s in synth for w in s["query"].split() if len(w) > 2))
    print(f"  weak corpus kept={len(weak['kept'])} reasons={weak['reasons']}")


if __name__ == "__main__":
    main()
