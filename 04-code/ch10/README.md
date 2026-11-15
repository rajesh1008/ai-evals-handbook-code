# Chapter 10 code: reference-based metrics and their limits

Run `./run_all.sh`. Output is in `OUTPUT.txt`; the analyses read cached model calls in `out/`.

| File | What it does |
|---|---|
| `fee200.py` | The 200 March 2027 fee traces Chapter 8 drew (seed 2026) and labelled under MC-02 v1.1: 162 pass, 23 deferred, 15 wrong (FM-06 10, FM-22 4, FM-24 1). Adds planted per-trace facts (loan digits, days late). |
| `replies.py` | Real model run: writes each trace's reply from a brief fixing what it must say. |
| `refs.py` | Two reference sets: `fee-refs-2027-05` (current, per situation, filled per trace) and Ryan's build-phase answer key from `fee-schedule-2024-01` text (stale). |
| `score.py` | Exact match, sentence BLEU, ROUGE-L, BERTScore, embedding cosine; cached per reference set. |
| `restyle.py` | Real model run: the same replies about 50% longer with the same decisions (a candidate's style). |
| `extract.py` | Fact extraction for partial credit: a fixed pattern against a real model extraction. |
| `lab.py` | AUCs with bootstrap intervals, length correlation, reading the 40 lowest, the cost of a catch-all cut-off, one reference per question, the cut-off carried to the longer style, roles, partial credit. |
| `inject.py` | Failure injection: the stale answer key, and ten planted ten-day grace replies against both keys and against the tool's value. |
| `try_its.py` | chrF; a wrong amount; a dropped negation in a contract clause. |

Truss 0.13 adds `truss/reference.py` (tests in `../truss/tests/test_ch10.py`).

## Model runs (1 November 2026, Asia/Calcutta)
All with `claude-haiku-4-5-20251001`, default temperature, one call per item:
replies 200 (33,024 input, 27,427 output tokens); restyle 200 (46,627 / 37,727); extraction 400.
The book text calls it "a small fast model". No other provider was run; those comparisons are marked [RESULT PENDING] in the book.

## Packages
`sacrebleu` 2.6.0, `rouge_score` is not needed (ROUGE-L is Truss's own, no stemming), `bert-score`
with `distilbert-base-uncased` (a small model chosen for CPU; the package default for English is
larger, so absolute BERTScore values differ from published ones), `fastembed` 0.9.1 with
`BAAI/bge-small-en-v1.5`, `torch` CPU. Install with `pip install --user sacrebleu bert-score fastembed`.

## What is planted
Reply texts are model-written from planted facts; the reference texts are fixture text; the
stale key's waiver wording is fixture text standing for the 2024 help-centre FAQ. Verdicts are
Chapter 8's MC-02 v1.1 labels, which come from the fixture's planted causes.
