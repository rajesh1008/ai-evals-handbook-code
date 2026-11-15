"""Chapter 23: evaluating retrieval and grounding (Truss 0.26).

What is here, in plain Python:
  recall_at_k, mrr, ndcg_at_k          ranking metrics against a labelled gold set
  hit_at_k                             whether any relevant chunk appears in the top k
  citation_support, groundedness_rate  claim-level support from retrieved passages
  chunk_coverage                       share of gold passages that a chunking covers
  index_staleness                      retired documents still retrievable
  filter_synthetic                     drop synthetic queries that are unanswerable or leaky
  embed_rank_agreement                 Spearman agreement of two embedding rankings
  RetrievalGold, IndexSnapshot         versioned gold queries and index digests
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence


_WORD = re.compile(r"[a-z0-9$%]+(?:[./-][a-z0-9]+)*")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def hit_at_k(ranked_ids: Sequence[str], relevant: set[str], k: int) -> float:
    """1.0 if any relevant id is in the top k, else 0.0."""
    top = list(ranked_ids)[:k]
    return 1.0 if any(i in relevant for i in top) else 0.0


def recall_at_k(ranked_ids: Sequence[str], relevant: set[str], k: int) -> float:
    """Share of relevant ids recovered in the top k. Empty relevant -> 0.0."""
    if not relevant:
        return 0.0
    top = set(list(ranked_ids)[:k])
    return len(top & relevant) / len(relevant)


def mrr(ranked_ids: Sequence[str], relevant: set[str]) -> float:
    """Mean reciprocal rank of the first relevant hit (one query)."""
    for i, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_ids: Sequence[str], relevance: dict[str, float], k: int) -> float:
    """Normalised discounted cumulative gain at k. Graded relevance map; missing -> 0."""
    def dcg(ids: Sequence[str]) -> float:
        total = 0.0
        for i, doc_id in enumerate(ids[:k], start=1):
            rel = float(relevance.get(doc_id, 0.0))
            if rel <= 0:
                continue
            total += (2 ** rel - 1.0) / math.log2(i + 1)
        return total

    ideal = sorted(relevance.values(), reverse=True)
    ideal_ids = [f"__ideal_{i}" for i in range(len(ideal))]
    ideal_map = {ideal_ids[i]: ideal[i] for i in range(len(ideal))}
    # compute ideal DCG directly
    ideal_dcg = 0.0
    for i, rel in enumerate(ideal[:k], start=1):
        if rel > 0:
            ideal_dcg += (2 ** rel - 1.0) / math.log2(i + 1)
    if ideal_dcg <= 0:
        return 0.0
    return dcg(ranked_ids) / ideal_dcg


def mean_metric(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion."""
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - margin) / denom, (centre + margin) / denom)


@dataclass(frozen=True)
class RetrievalGold:
    """A labelled retrieval query tied to relevant chunk ids and a source digest."""
    query_id: str
    query: str
    relevant: frozenset[str]
    source_digest: str
    graded: dict[str, float] = field(default_factory=dict)

    def digest(self) -> str:
        payload = f"{self.query_id}|{self.query}|{sorted(self.relevant)}|{self.source_digest}"
        return hashlib.sha256(payload.encode()).hexdigest()[:12]


@dataclass(frozen=True)
class IndexSnapshot:
    """Content-addressed view of what the retriever can see."""
    name: str
    chunk_ids: frozenset[str]
    retired_ids: frozenset[str] = frozenset()
    meta: dict = field(default_factory=dict)

    def digest(self) -> str:
        payload = f"{self.name}|{sorted(self.chunk_ids)}|{sorted(self.retired_ids)}"
        return hashlib.sha256(payload.encode()).hexdigest()[:12]


def index_staleness(snapshot: IndexSnapshot) -> dict:
    """Retired documents still present in the live index."""
    live_retired = sorted(snapshot.chunk_ids & snapshot.retired_ids)
    return {
        "n_chunks": len(snapshot.chunk_ids),
        "n_retired_live": len(live_retired),
        "retired_live": live_retired,
        "stale": bool(live_retired),
        "index_digest": snapshot.digest(),
    }


def citation_support(claim: str, passages: Sequence[str], min_overlap: float = 0.35) -> dict:
    """Does any passage support the claim by token overlap above a floor?"""
    claim_toks = set(_tokens(claim))
    if not claim_toks:
        return {"supported": False, "best": 0.0, "passage_index": None}
    best, best_i = 0.0, None
    for i, passage in enumerate(passages):
        pt = set(_tokens(passage))
        if not pt:
            continue
        overlap = len(claim_toks & pt) / len(claim_toks)
        if overlap > best:
            best, best_i = overlap, i
    return {
        "supported": best >= min_overlap,
        "best": best,
        "passage_index": best_i,
    }


def groundedness_rate(rows: Sequence[dict], min_overlap: float = 0.35) -> dict:
    """rows: {claim, passages: list[str]}. Returns rate and Wilson interval."""
    n = len(rows)
    ok = 0
    for row in rows:
        if citation_support(row["claim"], row.get("passages") or [], min_overlap)["supported"]:
            ok += 1
    lo, hi = wilson_interval(ok, n)
    return {"supported": ok, "n": n, "rate": (ok / n) if n else 0.0, "wilson": (lo, hi)}


def chunk_coverage(gold_passages: Sequence[str], chunks: Sequence[str], min_overlap: float = 0.5) -> dict:
    """Share of gold passages that at least one chunk covers by overlap."""
    covered = 0
    for gold in gold_passages:
        g = set(_tokens(gold))
        if not g:
            continue
        hit = False
        for ch in chunks:
            c = set(_tokens(ch))
            if c and len(g & c) / len(g) >= min_overlap:
                hit = True
                break
        if hit:
            covered += 1
    n = len(gold_passages)
    return {"covered": covered, "n": n, "rate": (covered / n) if n else 0.0}


def filter_synthetic(candidates: Sequence[dict], corpus_tokens: set[str]) -> dict:
    """Drop synthetic queries that are empty, too short, or unanswerable on the corpus.

    A candidate is answerable if at least two content tokens appear in the corpus.
    Returns kept, dropped-by-reason, and the filter digest.
    """
    kept, dropped = [], []
    reasons = {"too_short": 0, "unanswerable": 0, "duplicate": 0}
    seen = set()
    for c in candidates:
        q = (c.get("query") or "").strip()
        toks = [t for t in _tokens(q) if len(t) > 2]
        key = " ".join(toks)
        if len(toks) < 3:
            reasons["too_short"] += 1
            dropped.append({**c, "drop_reason": "too_short"})
            continue
        if key in seen:
            reasons["duplicate"] += 1
            dropped.append({**c, "drop_reason": "duplicate"})
            continue
        hits = sum(1 for t in set(toks) if t in corpus_tokens)
        if hits < 2:
            reasons["unanswerable"] += 1
            dropped.append({**c, "drop_reason": "unanswerable"})
            continue
        seen.add(key)
        kept.append(c)
    payload = f"{len(kept)}|{len(dropped)}|{sorted(reasons.items())}"
    return {
        "kept": kept,
        "dropped": dropped,
        "reasons": reasons,
        "filter_digest": hashlib.sha256(payload.encode()).hexdigest()[:12],
    }


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman rank correlation; requires equal non-empty lengths."""
    n = len(xs)
    if n != len(ys) or n == 0:
        raise ValueError("equal non-empty lengths required")

    def ranks(vals: Sequence[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: vals[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    deny = math.sqrt(sum((b - my) ** 2 for b in ry))
    if denx == 0 or deny == 0:
        return 0.0
    return num / (denx * deny)


def embed_rank_agreement(scores_a: Sequence[float], scores_b: Sequence[float]) -> float:
    """Agreement of two scoring functions over the same candidate list (Spearman)."""
    return spearman(scores_a, scores_b)


def evaluate_rankings(gold: Sequence[RetrievalGold], rankings: dict[str, Sequence[str]], k: int = 5) -> dict:
    """Aggregate recall@k, MRR, nDCG@k and hit@k over a gold set."""
    recalls, mrrs, ndcgs, hits = [], [], [], []
    for g in gold:
        ranked = rankings.get(g.query_id, [])
        recalls.append(recall_at_k(ranked, set(g.relevant), k))
        mrrs.append(mrr(ranked, set(g.relevant)))
        graded = g.graded or {rid: 1.0 for rid in g.relevant}
        ndcgs.append(ndcg_at_k(ranked, graded, k))
        hits.append(hit_at_k(ranked, set(g.relevant), k))
    hit_n = int(round(sum(hits)))
    lo, hi = wilson_interval(hit_n, len(hits))
    return {
        "n": len(gold),
        "k": k,
        "recall_at_k": mean_metric(recalls),
        "mrr": mean_metric(mrrs),
        "ndcg_at_k": mean_metric(ndcgs),
        "hit_at_k": mean_metric(hits),
        "hit_wilson": (lo, hi),
        "hit_count": hit_n,
    }
