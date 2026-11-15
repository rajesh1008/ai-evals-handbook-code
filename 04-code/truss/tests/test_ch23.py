"""Chapter 23 Truss 0.26 retrieval tests."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from truss.retrieval import (
    RetrievalGold,
    IndexSnapshot,
    citation_support,
    chunk_coverage,
    embed_rank_agreement,
    evaluate_rankings,
    filter_synthetic,
    hit_at_k,
    index_staleness,
    mrr,
    ndcg_at_k,
    recall_at_k,
    wilson_interval,
)


def test_recall_mrr_hit_basic():
    ranked = ["a", "b", "c", "d"]
    rel = {"c", "z"}
    assert recall_at_k(ranked, rel, 3) == 0.5
    assert hit_at_k(ranked, rel, 2) == 0.0
    assert hit_at_k(ranked, rel, 3) == 1.0
    assert mrr(ranked, rel) == 1.0 / 3


def test_ndcg_perfect_and_zero():
    rel = {"a": 2.0, "b": 1.0}
    assert abs(ndcg_at_k(["a", "b"], rel, 2) - 1.0) < 1e-9
    assert ndcg_at_k(["x", "y"], rel, 2) == 0.0


def test_wilson_and_grounding():
    lo, hi = wilson_interval(9, 10)
    assert 0.5 < lo < 0.9 < hi < 1.0
    s = citation_support("late fee is twenty five dollars", ["The late fee is $25 after the grace period."])
    assert s["supported"] is True
    s2 = citation_support("title release takes ten days", ["The late fee is $25."])
    assert s2["supported"] is False


def test_index_staleness_and_coverage():
    snap = IndexSnapshot(
        name="pilot",
        chunk_ids=frozenset({"fee-2026", "fee-2024", "hp"}),
        retired_ids=frozenset({"fee-2024"}),
    )
    st = index_staleness(snap)
    assert st["stale"] is True
    assert st["retired_live"] == ["fee-2024"]
    cov = chunk_coverage(
        ["grace period is fifteen days before a late fee"],
        ["Borrowers get a fifteen-day grace period before a late fee is charged."],
    )
    assert cov["rate"] == 1.0


def test_filter_synthetic_and_spearman():
    corpus = {"late", "fee", "grace", "period", "hardship", "deferral"}
    out = filter_synthetic(
        [
            {"query": "what is the late fee grace period"},
            {"query": "hi"},
            {"query": "quantum banana orchard zodiac"},
            {"query": "what is the late fee grace period"},
        ],
        corpus,
    )
    assert len(out["kept"]) == 1
    assert out["reasons"]["too_short"] == 1
    assert out["reasons"]["unanswerable"] == 1
    assert out["reasons"]["duplicate"] == 1
    assert abs(embed_rank_agreement([1, 2, 3], [1, 2, 3]) - 1.0) < 1e-9
    assert embed_rank_agreement([1, 2, 3], [3, 2, 1]) < 0


def test_evaluate_rankings_aggregate():
    gold = [
        RetrievalGold("q1", "grace", frozenset({"a"}), "d1", {"a": 2.0}),
        RetrievalGold("q2", "fee", frozenset({"b"}), "d1", {"b": 1.0}),
    ]
    rankings = {"q1": ["a", "x"], "q2": ["x", "b"]}
    rep = evaluate_rankings(gold, rankings, k=2)
    assert rep["n"] == 2
    assert abs(rep["hit_at_k"] - 1.0) < 1e-9
    assert abs(rep["mrr"] - (1.0 + 0.5) / 2) < 1e-9


def test_gold_and_index_digests_stable():
    g = RetrievalGold("q1", "grace period", frozenset({"c1"}), "src")
    assert len(g.digest()) == 12
    assert g.digest() == g.digest()
    s = IndexSnapshot("live", frozenset({"c1", "c2"}))
    assert len(s.digest()) == 12
