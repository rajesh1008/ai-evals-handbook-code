"""Failure injection: stale index serving a superseded fee schedule."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from truss.retrieval import IndexSnapshot, evaluate_rankings, index_staleness, RetrievalGold
from corpus import live_chunk_ids, retired_chunk_ids
from fixture import build_gold, rankings_for_index, production_cases, RANK_SEED


def main():
    gold_rows = build_gold(90)
    gold = [
        RetrievalGold(g["query_id"], g["query"], frozenset(g["relevant"]), g["source_digest"], dict(g["graded"]))
        for g in gold_rows
    ]
    live = live_chunk_ids()
    retired = retired_chunk_ids()
    stale = IndexSnapshot("inject-stale", frozenset(live | retired), frozenset(retired))
    print("Injection: stale index with retired fee-schedule-2024-01 chunks")
    print(index_staleness(stale))
    rank = rankings_for_index(gold_rows, live | retired, noise=0.55, seed=RANK_SEED + 1)
    rep = evaluate_rankings(gold, rank, k=5)
    print(
        f"metrics under injection: recall@5={rep['recall_at_k']:.3f} "
        f"MRR={rep['mrr']:.3f} hit@5={rep['hit_at_k']:.3f}"
    )
    # fee-specific subset
    fee = [g for g in gold if any(r.startswith("fee-schedule-2026-03") for r in g.relevant)]
    fee_rank = {g.query_id: rank[g.query_id] for g in fee}
    fee_rep = evaluate_rankings(fee, fee_rank, k=5)
    print(
        f"fee subset n={fee_rep['n']}: recall@5={fee_rep['recall_at_k']:.3f} "
        f"hit@5={fee_rep['hit_count']}/{fee_rep['n']}"
    )
    # how often retired chunk ranks above current for fee queries
    inverted = 0
    for g in fee:
        ordered = rank[g.query_id]
        cur = [c for c in ordered if c.startswith("fee-schedule-2026-03")]
        old = [c for c in ordered if c.startswith("fee-schedule-2024-01")]
        if old and cur and ordered.index(old[0]) < ordered.index(cur[0]):
            inverted += 1
    print(f"fee queries where retired chunk outranks current: {inverted}/{len(fee)}")
    print("production cases under the same failure mode:")
    for c in production_cases():
        print(f"  {c['trace_id']}: {c['note']}")


if __name__ == "__main__":
    main()
