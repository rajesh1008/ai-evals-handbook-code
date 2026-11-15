"""Deterministic retrieval gold set and simulated rankings for Chapter 23.

SIMULATED: query labels, rankings under each index, and officer groundedness
labels. Seed 2026. Real Anthropic calls live in real_grounding.py.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from corpus import CORPUS, live_chunk_ids, retired_chunk_ids

SEED = 2026
RANK_SEED = 2032  # chosen so live recall@5 == 0.91 under noise=0.40


GOLD_SPECS = [
    # (qid, query, relevant chunk ids, graded weights)
    ("rq-001", "how many days of grace before a late fee", ["fee-schedule-2026-03::grace"], {"fee-schedule-2026-03::grace": 2.0}),
    ("rq-002", "what is the late fee amount", ["fee-schedule-2026-03::amount"], {"fee-schedule-2026-03::amount": 2.0}),
    ("rq-003", "can autopay get a courtesy late fee waiver", ["fee-schedule-2026-03::waiver"], {"fee-schedule-2026-03::waiver": 2.0}),
    ("rq-004", "returned payment fee amount", ["fee-schedule-2026-03::returned"], {"fee-schedule-2026-03::returned": 2.0}),
    ("rq-005", "how often can a borrower get hardship relief", ["hardship-policy-2027-04::window"], {"hardship-policy-2027-04::window": 2.0}),
    ("rq-006", "must income be confirmed before a hardship offer", ["hardship-policy-2027-04::income"], {"hardship-policy-2027-04::income": 2.0}),
    ("rq-007", "what events make a borrower hardship eligible", ["hardship-policy-2027-04::eligibility"], {"hardship-policy-2027-04::eligibility": 2.0}),
    ("rq-008", "how soon after payoff is the title released", ["lien-release-guide-2026-02::timing"], {"lien-release-guide-2026-02::timing": 2.0}),
    ("rq-009", "what does a payoff letter include", ["payoff-procedures-2026-01::letter"], {"payoff-procedures-2026-01::letter": 2.0}),
    ("rq-010", "how far back can I get monthly statements", ["statement-guide-2025-11::history"], {"statement-guide-2025-11::history": 2.0}),
]


def _overlap_score(query: str, text: str) -> float:
    qt = set(w for w in query.lower().split() if len(w) > 2)
    tt = set(w for w in text.lower().split() if len(w) > 2)
    if not qt:
        return 0.0
    return len(qt & tt) / len(qt)


def rank_chunks(query: str, chunk_ids: set[str], noise: float, rng: random.Random) -> list[str]:
    scored = []
    for cid in sorted(chunk_ids):
        base = _overlap_score(query, CORPUS[cid]["text"])
        # slight lexical boost for exact section keywords
        if "grace" in query and "grace" in cid:
            base += 0.12
        if "late fee amount" in query and "amount" in cid:
            base += 0.12
        if "waiver" in query or "autopay" in query:
            if "waiver" in cid:
                base += 0.15
        if "returned" in query and "returned" in cid:
            base += 0.15
        if "hardship" in query and "hardship" in cid:
            base += 0.08
        if "income" in query and "income" in cid:
            base += 0.12
        if "eligible" in query and "eligibility" in cid:
            base += 0.12
        if "title" in query or "lien" in query or "release" in query:
            if "lien" in cid:
                base += 0.15
        if "payoff letter" in query and "letter" in cid:
            base += 0.15
        if "statement" in query and "history" in cid:
            base += 0.15
        scored.append((base + rng.uniform(0, noise), cid))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [cid for _, cid in scored]


def build_gold(n_extra: int = 90):
    """110 labelled queries: 10 templates + 90 paraphrases (SIMULATED officer labels)."""
    r = random.Random(SEED)
    gold = []
    source = hashlib.sha256("harbor-policy-gold-2028-03".encode()).hexdigest()[:12]
    for qid, query, rel, graded in GOLD_SPECS:
        gold.append({
            "query_id": qid,
            "query": query,
            "relevant": set(rel),
            "graded": dict(graded),
            "source_digest": source,
            "kind": "template",
        })
    # paraphrases inherit labels from a template
    paraphrases = {
        "rq-001": [
            "grace period length for late fees",
            "when does the late fee clock start after the due date",
            "is there a grace window before charging a late fee",
        ],
        "rq-002": [
            "how much do you charge for a late payment",
            "dollar amount of the late fee",
            "late fee dollars after grace ends",
        ],
        "rq-003": [
            "autopay courtesy waiver rules",
            "can I get a late fee waived on autopay",
            "twelve month courtesy waiver for autopay",
        ],
        "rq-004": [
            "NSF or returned payment fee",
            "bounce fee for a returned payment",
            "what is the returned payment charge",
        ],
        "rq-005": [
            "hardship arrangement frequency limit",
            "months between hardship helps",
            "can I get hardship twice in one year",
        ],
        "rq-006": [
            "income check before drafting hardship",
            "do we need expenses confirmed for hardship",
            "hardship offer without income documents",
        ],
        "rq-007": [
            "hardship eligible situations",
            "medical bills and hardship",
            "disaster county hardship eligibility",
        ],
        "rq-008": [
            "lien release after payoff timing",
            "title release business days",
            "how long until title comes after payoff",
        ],
        "rq-009": [
            "payoff quote letter contents",
            "good through date on payoff letter",
            "what fields appear on a payoff letter",
        ],
        "rq-010": [
            "statement history depth in months",
            "can Compass send two years of statements",
            "older than twenty four months statements",
        ],
    }
    i = 0
    while len(gold) < 10 + n_extra:
        parent = GOLD_SPECS[i % len(GOLD_SPECS)]
        opts = paraphrases[parent[0]]
        q = r.choice(opts)
        # occasional harder wording
        if r.random() < 0.2:
            q = q + " for my auto loan"
        qid = f"rq-{len(gold)+1:03d}"
        gold.append({
            "query_id": qid,
            "query": q,
            "relevant": set(parent[2]),
            "graded": dict(parent[3]),
            "source_digest": source,
            "kind": "paraphrase",
            "parent": parent[0],
        })
        i += 1
    return gold


def rankings_for_index(gold, chunk_ids, noise=0.08, seed=SEED):
    r = random.Random(seed)
    out = {}
    for g in gold:
        out[g["query_id"]] = rank_chunks(g["query"], set(chunk_ids), noise, r)
    return out


def production_cases():
    """Two wrong-fee cases traced to retrieval, not generation (SIMULATED labels)."""
    return [
        {
            "trace_id": "t-262418",
            "date": "2028-03-22",
            "query": "how many days before a late fee",
            "retrieved": ["fee-schedule-2024-01::grace", "fee-schedule-2026-03::grace"],
            "reply_claim": "You have a ten-day grace period before a late fee.",
            "root_cause": "retrieval",
            "note": "stale chunk ranked first; generator faithfully quoted it",
        },
        {
            "trace_id": "t-263055",
            "date": "2028-03-24",
            "query": "what is the late fee",
            "retrieved": ["fee-schedule-2024-01::amount", "fee-schedule-2026-03::waiver"],
            "reply_claim": "The late fee is thirty dollars.",
            "root_cause": "retrieval",
            "note": "retired amount chunk; current amount chunk not in top 2",
        },
    ]


def grounding_rows(gold, rankings, k=5):
    """Build claim/passage rows for groundedness (SIMULATED claims from gold)."""
    rows = []
    claim_map = {
        "grace": "The grace period is fifteen days before a late fee.",
        "amount": "The late fee is twenty-five dollars.",
        "waiver": "Autopay borrowers get one courtesy waiver in twelve months.",
        "returned": "A returned payment fee is fifteen dollars.",
        "window": "Hardship is once in twelve calendar months.",
        "income": "Income must be confirmed before drafting a hardship offer.",
        "eligibility": "Medical expense spikes can make a borrower hardship eligible.",
        "timing": "Lien release is requested within five business days after payoff.",
        "letter": "A payoff letter includes the good-through date and per-diem.",
        "history": "Compass can send statements for the most recent twenty-four months.",
    }
    for g in gold:
        rel = next(iter(g["relevant"]))
        section = rel.split("::")[1]
        claim = claim_map[section]
        passages = [CORPUS[cid]["text"] for cid in rankings[g["query_id"]][:k]]
        rows.append({"query_id": g["query_id"], "claim": claim, "passages": passages, "relevant": rel})
    return rows


def chunkings():
    """Three chunking strategies over the live corpus (character windows)."""
    docs = {}
    for cid, c in CORPUS.items():
        if c["retired"]:
            continue
        docs.setdefault(c["doc"], []).append(c["text"])
    full_texts = {d: " ".join(parts) for d, parts in docs.items()}

    def windows(text, size, stride):
        out = []
        i = 0
        while i < len(text):
            out.append(text[i:i + size])
            if i + size >= len(text):
                break
            i += stride
        return out

    return {
        "chars_180_overlap_40": {d: windows(t, 180, 140) for d, t in full_texts.items()},
        "chars_320_overlap_80": {d: windows(t, 320, 240) for d, t in full_texts.items()},
        "section_native": {d: docs[d] for d in docs},
    }


def bag_embed(text: str) -> dict[str, float]:
    """Tiny hashed bag-of-words embedding stand-in (deterministic)."""
    vec = {}
    for w in text.lower().split():
        w = "".join(ch for ch in w if ch.isalnum())
        if len(w) < 3:
            continue
        # 32-dim hashed bag
        h = int(hashlib.md5(w.encode()).hexdigest(), 16) % 32
        vec[h] = vec.get(h, 0.0) + 1.0
    # L2
    norm = sum(v * v for v in vec.values()) ** 0.5 or 1.0
    return {k: v / norm for k, v in vec.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)


def embed_scores(query: str, chunk_ids, variant="A"):
    qv = bag_embed(query + (" policy fee" if variant == "B" else ""))
    scores = []
    for cid in sorted(chunk_ids):
        text = CORPUS[cid]["text"]
        if variant == "B":
            text = text + " " + CORPUS[cid]["doc"]
        scores.append(cosine(qv, bag_embed(text)))
    return scores
