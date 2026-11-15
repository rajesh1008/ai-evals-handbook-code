# Chapter 11 lab: evaluating extraction and structured outputs

Harbor Lending's document reader for the hardship income step (HP-2027-04 section 4.2), scored field by field.

## Files
| File | What it does |
|---|---|
| `docs.py` | Generates 200 uploaded documents (hd-0001 to hd-0200; 90 pay stubs, 60 bank statements, 50 hardship letters; 30 layouts; 32 in Spanish; 42 photographed with OCR character swaps), each with its gold record. Seed 2026; `out/docs.jsonl` md5 99c02bdbf19c0f17b1fa1afcb79fc4c2. Uploads Mon 3 to Fri 28 May 2027, never before the period a document covers ends. |
| `extract.py` | Real model runs, cached: claude-haiku-4-5-20251001 (Compass's extractor) and claude-sonnet-4-6 (second reader), prompt `extract-prompt-v1`. |
| `specs.py` | Twelve field specifications (type, required, critical, tolerance). |
| `score.py` | Outcomes per field (tp, wrong, miss, invented, tn) and an illustrative HP-2027-04 income decision (recency, payment-to-income band; letters add loan and route). |
| `lab.py` | Layer one, per-field table, documents and decisions, Victor's threshold, slices, error classes, payroll table, confidence, second reader, definitions, after-fix rerun. Writes `out/scores.json`. |
| `inject.py` | Failure injection: a normaliser that rounds money to whole dollars, scored under three tolerances. |
| `sql_lab.py` | Account-lookup Text2SQL, 30 questions about borrower 1007, execution on `dev.db` and `probe.db` (data date Thu 20 May 2027). Real model run, cached. |
| `try_its.py` | The chapter's three Try It Yourself variations (the Spanish rerun is a real model run, prompt `extract-prompt-v2`, cached). |
| `run_all.sh` | Runs everything from the caches and writes `OUTPUT.txt`, then the Truss tests. |

## Models and runs
- Runs made on 1 November 2026 (Asia/Calcutta) through the Anthropic API. Tokens: Haiku 168,039 input / 70,108 output; Sonnet 168,039 input / 69,684 output, for 200 documents each.
- Default sampling temperature: the installed SDK refused a `temperature` argument, so reruns can differ slightly; the cached replies in `out/` are the ones scored.
- Runs on other providers have not been made; the book marks them [RESULT PENDING].

## Rerun
```
cd 04-code/ch11
./run_all.sh            # from caches, no API calls
rm out/extract-*.jsonl out/sql-haiku.jsonl && ./run_all.sh   # fresh model calls; needs ANTHROPIC_API_KEY in the environment
```
The key is read from the environment only and is never written to any file.

## Story dates (illustrative)
Guideline v3 and Victor's threshold frozen Fri 14 May 2027; scoring Tue 1 June; ruling Fri 4 June 2027. Document IDs are used instead of trace IDs, so the next trace ID stays t-108195.
