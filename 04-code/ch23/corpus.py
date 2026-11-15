"""Harbor Lending policy corpus for Chapter 23 retrieval evals.

Documents and chunk ids are the labelled units. The retired fee schedule is
kept for the stale-index injection; live indexes exclude it.
"""
from __future__ import annotations

CORPUS = {
    "fee-schedule-2026-03::grace": {
        "doc": "fee-schedule-2026-03",
        "section": "grace",
        "text": (
            "Late fee grace period. A payment is late after a fifteen-day grace period "
            "from the due date. No late fee is charged during the grace period."
        ),
        "retired": False,
    },
    "fee-schedule-2026-03::amount": {
        "doc": "fee-schedule-2026-03",
        "section": "amount",
        "text": (
            "Late fee amount. The late fee is twenty-five dollars ($25) once the grace "
            "period ends, applied once per late payment event."
        ),
        "retired": False,
    },
    "fee-schedule-2026-03::waiver": {
        "doc": "fee-schedule-2026-03",
        "section": "waiver",
        "text": (
            "Courtesy waiver. One late-fee waiver is available in any twelve-month window "
            "for borrowers on autopay. The waiver is applied without a phone call when "
            "the account meets the autopay rule."
        ),
        "retired": False,
    },
    "fee-schedule-2026-03::returned": {
        "doc": "fee-schedule-2026-03",
        "section": "returned",
        "text": (
            "Returned-payment fee. A returned payment incurs a fifteen-dollar ($15) fee "
            "in addition to any late fee that later applies."
        ),
        "retired": False,
    },
    "fee-schedule-2024-01::grace": {
        "doc": "fee-schedule-2024-01",
        "section": "grace",
        "text": (
            "Late fee grace period (retired). A payment is late after a ten-day grace period "
            "from the due date. This schedule was retired on 1 March 2026."
        ),
        "retired": True,
    },
    "fee-schedule-2024-01::amount": {
        "doc": "fee-schedule-2024-01",
        "section": "amount",
        "text": (
            "Late fee amount (retired). The late fee is thirty dollars ($30). "
            "Retired on 1 March 2026."
        ),
        "retired": True,
    },
    "hardship-policy-2027-04::window": {
        "doc": "hardship-policy-2027-04",
        "section": "window",
        "text": (
            "Hardship window. A borrower may receive one hardship arrangement in any "
            "twelve calendar months, counted from the start date of the prior arrangement."
        ),
        "retired": False,
    },
    "hardship-policy-2027-04::income": {
        "doc": "hardship-policy-2027-04",
        "section": "income",
        "text": (
            "Income and expenses. Before drafting an offer, Compass must confirm income "
            "and essential expenses with a document or a stated figure the officer accepts."
        ),
        "retired": False,
    },
    "hardship-policy-2027-04::eligibility": {
        "doc": "hardship-policy-2027-04",
        "section": "eligibility",
        "text": (
            "Eligibility. Hardship relief covers temporary loss of income, medical expense "
            "spikes, and disaster declarations that affect the borrower's county."
        ),
        "retired": False,
    },
    "lien-release-guide-2026-02::timing": {
        "doc": "lien-release-guide-2026-02",
        "section": "timing",
        "text": (
            "Title release timing. After payoff clears, Harbor Lending requests the lien "
            "release within five business days and tracks delivery to the borrower."
        ),
        "retired": False,
    },
    "payoff-procedures-2026-01::letter": {
        "doc": "payoff-procedures-2026-01",
        "section": "letter",
        "text": (
            "Payoff letter. A payoff letter states the good-through date, the per-diem, "
            "the total due, and the wiring instructions. Amounts are rendered by the "
            "document service, not by the chat model."
        ),
        "retired": False,
    },
    "statement-guide-2025-11::history": {
        "doc": "statement-guide-2025-11",
        "section": "history",
        "text": (
            "Statement history. Borrowers may request monthly statements for the most "
            "recent twenty-four months through Compass; older statements go to an officer."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-01": {
        "doc": "ops-handbook-2026",
        "section": "note-01",
        "text": (
            "Operations note 1. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 1, queue 2, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-02": {
        "doc": "ops-handbook-2026",
        "section": "note-02",
        "text": (
            "Operations note 2. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 2, queue 3, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-03": {
        "doc": "ops-handbook-2026",
        "section": "note-03",
        "text": (
            "Operations note 3. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 3, queue 4, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-04": {
        "doc": "ops-handbook-2026",
        "section": "note-04",
        "text": (
            "Operations note 4. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 4, queue 5, region 1."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-05": {
        "doc": "ops-handbook-2026",
        "section": "note-05",
        "text": (
            "Operations note 5. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 5, queue 6, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-06": {
        "doc": "ops-handbook-2026",
        "section": "note-06",
        "text": (
            "Operations note 6. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 6, queue 7, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-07": {
        "doc": "ops-handbook-2026",
        "section": "note-07",
        "text": (
            "Operations note 7. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 7, queue 1, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-08": {
        "doc": "ops-handbook-2026",
        "section": "note-08",
        "text": (
            "Operations note 8. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 8, queue 2, region 1."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-09": {
        "doc": "ops-handbook-2026",
        "section": "note-09",
        "text": (
            "Operations note 9. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 9, queue 3, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-10": {
        "doc": "ops-handbook-2026",
        "section": "note-10",
        "text": (
            "Operations note 10. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 10, queue 4, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-11": {
        "doc": "ops-handbook-2026",
        "section": "note-11",
        "text": (
            "Operations note 11. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 11, queue 5, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-12": {
        "doc": "ops-handbook-2026",
        "section": "note-12",
        "text": (
            "Operations note 12. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 12, queue 6, region 1."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-13": {
        "doc": "ops-handbook-2026",
        "section": "note-13",
        "text": (
            "Operations note 13. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 13, queue 7, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-14": {
        "doc": "ops-handbook-2026",
        "section": "note-14",
        "text": (
            "Operations note 14. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 14, queue 1, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-15": {
        "doc": "ops-handbook-2026",
        "section": "note-15",
        "text": (
            "Operations note 15. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 15, queue 2, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-16": {
        "doc": "ops-handbook-2026",
        "section": "note-16",
        "text": (
            "Operations note 16. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 16, queue 3, region 1."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-17": {
        "doc": "ops-handbook-2026",
        "section": "note-17",
        "text": (
            "Operations note 17. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 17, queue 4, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-18": {
        "doc": "ops-handbook-2026",
        "section": "note-18",
        "text": (
            "Operations note 18. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 18, queue 5, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-19": {
        "doc": "ops-handbook-2026",
        "section": "note-19",
        "text": (
            "Operations note 19. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 19, queue 6, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-20": {
        "doc": "ops-handbook-2026",
        "section": "note-20",
        "text": (
            "Operations note 20. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 20, queue 7, region 1."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-21": {
        "doc": "ops-handbook-2026",
        "section": "note-21",
        "text": (
            "Operations note 21. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 21, queue 1, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-22": {
        "doc": "ops-handbook-2026",
        "section": "note-22",
        "text": (
            "Operations note 22. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 22, queue 2, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-23": {
        "doc": "ops-handbook-2026",
        "section": "note-23",
        "text": (
            "Operations note 23. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 23, queue 3, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-24": {
        "doc": "ops-handbook-2026",
        "section": "note-24",
        "text": (
            "Operations note 24. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 24, queue 4, region 1."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-25": {
        "doc": "ops-handbook-2026",
        "section": "note-25",
        "text": (
            "Operations note 25. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 25, queue 5, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-26": {
        "doc": "ops-handbook-2026",
        "section": "note-26",
        "text": (
            "Operations note 26. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 26, queue 6, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-27": {
        "doc": "ops-handbook-2026",
        "section": "note-27",
        "text": (
            "Operations note 27. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 27, queue 7, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-28": {
        "doc": "ops-handbook-2026",
        "section": "note-28",
        "text": (
            "Operations note 28. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 28, queue 1, region 1."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-29": {
        "doc": "ops-handbook-2026",
        "section": "note-29",
        "text": (
            "Operations note 29. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 29, queue 2, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-30": {
        "doc": "ops-handbook-2026",
        "section": "note-30",
        "text": (
            "Operations note 30. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 30, queue 3, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-31": {
        "doc": "ops-handbook-2026",
        "section": "note-31",
        "text": (
            "Operations note 31. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 31, queue 4, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-32": {
        "doc": "ops-handbook-2026",
        "section": "note-32",
        "text": (
            "Operations note 32. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 32, queue 5, region 1."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-33": {
        "doc": "ops-handbook-2026",
        "section": "note-33",
        "text": (
            "Operations note 33. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 33, queue 6, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-34": {
        "doc": "ops-handbook-2026",
        "section": "note-34",
        "text": (
            "Operations note 34. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 34, queue 7, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-35": {
        "doc": "ops-handbook-2026",
        "section": "note-35",
        "text": (
            "Operations note 35. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 35, queue 1, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-36": {
        "doc": "ops-handbook-2026",
        "section": "note-36",
        "text": (
            "Operations note 36. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 36, queue 2, region 1."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-37": {
        "doc": "ops-handbook-2026",
        "section": "note-37",
        "text": (
            "Operations note 37. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 37, queue 3, region 2."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-38": {
        "doc": "ops-handbook-2026",
        "section": "note-38",
        "text": (
            "Operations note 38. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 38, queue 4, region 3."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-39": {
        "doc": "ops-handbook-2026",
        "section": "note-39",
        "text": (
            "Operations note 39. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 39, queue 5, region 4."
        ),
        "retired": False,
    },
    "ops-handbook-2026::note-40": {
        "doc": "ops-handbook-2026",
        "section": "note-40",
        "text": (
            "Operations note 40. Staff routing guidance for queues, hours, and escalation "
            "paths. This note does not set borrower-facing fee, hardship, lien, payoff or "
            "statement policy. Topic tags: desk 40, queue 6, region 1."
        ),
        "retired": False,
    },
}


def live_chunk_ids():
    return {cid for cid, c in CORPUS.items() if not c["retired"]}


def retired_chunk_ids():
    return {cid for cid, c in CORPUS.items() if c["retired"]}


def corpus_tokens():
    toks = set()
    for c in CORPUS.values():
        if c["retired"]:
            continue
        for w in c["text"].lower().replace("$", " ").replace("(", " ").replace(")", " ").split():
            w = "".join(ch for ch in w if ch.isalnum() or ch in "-")
            if len(w) > 2:
                toks.add(w)
    return toks
