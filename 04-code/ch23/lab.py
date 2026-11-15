"""Chapter 23 lab: evaluate Compass policy retrieval and grounding.

SIMULATED rankings and gold labels (seed 2026). Truss computations are real.
Optional live grounding judgements: see real_grounding.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "truss"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from truss.retrieval import (
    IndexSnapshot,
    RetrievalGold,
    chunk_coverage,
    embed_rank_agreement,
    evaluate_rankings,
    filter_synthetic,
    groundedness_rate,
    index_staleness,
)
from corpus import CORPUS, corpus_tokens, live_chunk_ids, retired_chunk_ids
from fixture import (
    SEED,
    RANK_SEED,
    build_gold,
    chunkings,
    embed_scores,
    grounding_rows,
    production_cases,
    rankings_for_index,
)


def as_gold(rows):
    return [
        RetrievalGold(
            query_id=g["query_id"],
            query=g["query"],
            relevant=frozenset(g["relevant"]),
            source_digest=g["source_digest"],
            graded=dict(g["graded"]),
        )
        for g in rows
    ]


def main():
    gold_rows = build_gold(90)
    gold = as_gold(gold_rows)
    live = live_chunk_ids()
    retired = retired_chunk_ids()

    live_snap = IndexSnapshot("live-2028-03", frozenset(live), frozenset(retired))
    stale_snap = IndexSnapshot(
        "stale-pilot",
        frozenset(live | retired),
        frozenset(retired),
    )

    print("Chapter 23 lab: evaluating retrieval and grounding")
    print(f"seed {SEED}; gold queries {len(gold)}; live chunks {len(live)}; retired {len(retired)}")
    print(f"live index digest {live_snap.digest()}; stale index digest {stale_snap.digest()}")
    print()

    print("1. Index staleness")
    print("  live :", index_staleness(live_snap))
    print("  stale:", index_staleness(stale_snap))
    print()

    live_rank = rankings_for_index(gold_rows, live, noise=0.40, seed=RANK_SEED)
    stale_rank = rankings_for_index(gold_rows, live | retired, noise=0.55, seed=RANK_SEED + 1)

    print("2. Ranking metrics on the gold set (k=5)")
    live_rep = evaluate_rankings(gold, live_rank, k=5)
    stale_rep = evaluate_rankings(gold, stale_rank, k=5)
    for name, rep in [("live", live_rep), ("stale", stale_rep)]:
        print(
            f"  {name}: n={rep['n']} recall@5={rep['recall_at_k']:.3f} "
            f"MRR={rep['mrr']:.3f} nDCG@5={rep['ndcg_at_k']:.3f} "
            f"hit@5={rep['hit_at_k']:.3f} ({rep['hit_count']}/{rep['n']}) "
            f"Wilson {rep['hit_wilson'][0]:.3f} to {rep['hit_wilson'][1]:.3f}"
        )
    # Harbor design target: recall@5 at 0.91 on the live index
    print(f"  Harbor touchpoint target recall@5=0.91; observed live={live_rep['recall_at_k']:.3f}")
    print()

    print("3. Production wrong-fee cases traced to retrieval")
    for case in production_cases():
        print(
            f"  {case['trace_id']} {case['date']}: retrieved {case['retrieved']}; "
            f"claim={case['reply_claim']!r}; root_cause={case['root_cause']}"
        )
    print()

    print("4. Groundedness on claims against top-5 passages (SIMULATED claims)")
    rows = grounding_rows(gold_rows, live_rank, k=5)
    g_live = groundedness_rate(rows, min_overlap=0.35)
    rows_stale = grounding_rows(gold_rows, stale_rank, k=5)
    g_stale = groundedness_rate(rows_stale, min_overlap=0.35)
    print(
        f"  live  supported {g_live['supported']}/{g_live['n']} "
        f"rate={g_live['rate']:.3f} Wilson {g_live['wilson'][0]:.3f} to {g_live['wilson'][1]:.3f}"
    )
    print(
        f"  stale supported {g_stale['supported']}/{g_stale['n']} "
        f"rate={g_stale['rate']:.3f} Wilson {g_stale['wilson'][0]:.3f} to {g_stale['wilson'][1]:.3f}"
    )
    print()

    print("5. Chunking coverage of gold passages")
    gold_passages = [CORPUS[next(iter(g['relevant']))]["text"] for g in gold_rows]
    for name, chunks_by_doc in chunkings().items():
        flat = [c for parts in chunks_by_doc.values() for c in parts]
        cov = chunk_coverage(gold_passages, flat, min_overlap=0.5)
        print(f"  {name}: covered {cov['covered']}/{cov['n']} rate={cov['rate']:.3f} n_chunks={len(flat)}")
    print()

    print("6. Synthetic queries filtered against the live corpus")
    synth = [
        {"query": "what is the late fee grace period"},
        {"query": "how much is the returned payment fee"},
        {"query": "hi there"},
        {"query": "quantum banana orchard zodiac rituals"},
        {"query": "when is hardship available after a prior deferral"},
        {"query": "what is the late fee grace period"},
        {"query": "payoff letter good-through date fields"},
        {"query": "alien spaceship refinance APR"},
    ]
    # expand with template noise
    for i in range(40):
        synth.append({"query": f"tell me about policy topic {i} vaguely please"})
    filt = filter_synthetic(synth, corpus_tokens())
    print(
        f"  kept {len(filt['kept'])} dropped {len(filt['dropped'])} "
        f"reasons={filt['reasons']} digest={filt['filter_digest']}"
    )
    print()

    print("7. Choosing an embedding stand-in on this corpus (bag-of-words A vs B)")
    # compare ranking agreement and hit@5 under each variant
    chunk_list = sorted(live)
    agree = []
    hits_a = hits_b = 0
    for g in gold_rows:
        sa = embed_scores(g["query"], chunk_list, "A")
        sb = embed_scores(g["query"], chunk_list, "B")
        agree.append(embed_rank_agreement(sa, sb))
        order_a = [cid for _, cid in sorted(zip(sa, chunk_list), key=lambda x: (-x[0], x[1]))]
        order_b = [cid for _, cid in sorted(zip(sb, chunk_list), key=lambda x: (-x[0], x[1]))]
        rel = g["relevant"]
        if any(c in rel for c in order_a[:5]):
            hits_a += 1
        if any(c in rel for c in order_b[:5]):
            hits_b += 1
    print(
        f"  mean Spearman(A,B)={sum(agree)/len(agree):.3f}; "
        f"hit@5 A={hits_a}/{len(gold_rows)} B={hits_b}/{len(gold_rows)}"
    )
    print()

    print("8. Where retrieval metrics fail to predict answer quality")
    # cases: high hit@5 but unsupported claim (wrong chunk paraphrased), and low hit with right parametric answer
    high_retr_bad_answer = 0
    low_retr_ok_answer = 0
    for g in gold_rows[:40]:
        ranked = live_rank[g["query_id"]]
        hit = any(c in g["relevant"] for c in ranked[:5])
        # simulate: 8% of hits still yield unsupported answers (generator ignores passage)
        # and 5% of misses still yield correct parametric answers
        h = int(hashlib_sha(g["query_id"]), 16)
        if hit and (h % 100) < 8:
            high_retr_bad_answer += 1
        if (not hit) and (h % 100) < 5:
            low_retr_ok_answer += 1
    print(
        f"  among first 40: high-retrieval unsupported answers={high_retr_bad_answer}; "
        f"low-retrieval parametric-correct={low_retr_ok_answer}"
    )
    print()

    # persist summary for figures
    out = {
        "live_rep": {k: (list(v) if isinstance(v, tuple) else v) for k, v in live_rep.items()},
        "stale_rep": {k: (list(v) if isinstance(v, tuple) else v) for k, v in stale_rep.items()},
        "g_live": {**g_live, "wilson": list(g_live["wilson"])},
        "g_stale": {**g_stale, "wilson": list(g_stale["wilson"])},
        "filt_reasons": filt["reasons"],
        "hits_embed": {"A": hits_a, "B": hits_b, "n": len(gold_rows)},
        "spearman": sum(agree) / len(agree),
        "cases": production_cases(),
    }
    Path(__file__).resolve().parent.joinpath("out").mkdir(exist_ok=True)
    Path(__file__).resolve().parent.joinpath("out/summary.json").write_text(json.dumps(out, indent=2))
    print("wrote out/summary.json")


def hashlib_sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()


if __name__ == "__main__":
    main()
