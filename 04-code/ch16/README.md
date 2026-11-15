> **Evidence status (2026-11-08 Asia/Calcutta):** Authorised NEW full study is run id `ch16-full-new-2026-11-08-2131` under `new_run/ch16-full-new-2026-11-08-2131/out/`. Historical `out/*.jsonl` full caches remain **absent** (see `out/MISSING_CACHES.md`) and are **not** recovered. Immutable `OUTPUT.txt` and `modest_*` stay as legacy/historical only — do not silently adopt their perfect scores. Set `CH16_OUT` to the NEW `out/` directory for offline `lab.py` / `inject.py` / `try_its.py`.

# Chapter 16 lab: the MC-02 fee-explanation judge

Build, measure and admit Harbor Lending's first production judge (monitoring tier, role *order*; **not** decide). Traffic and planted labels are SIMULATED (`fixture.py`, seed 2026). Reply text and every judge or agent verdict quoted in the chapter come from the **NEW** REAL Anthropic run `ch16-full-new-2026-11-08-2131` (pinned `claude-haiku-4-5-20251001` / `claude-sonnet-4-5-20250929`). Scoring authority: `common.score` (abstain in TPR/TNR denominators). Run report: `new_run/ch16-full-new-2026-11-08-2131/reports/NEW_RESULTS.md`.

A separate **modest** n=24 study (`out/modest_study/`, `ch16-modest-2026-11-08`) is left untouched and is not the n=200 study.

## What to run (offline against NEW caches)

```bash
export CH16_OUT=$PWD/new_run/ch16-full-new-2026-11-08-2131/out
python3 lab.py        # every number the chapter quotes (writes $CH16_OUT/lab.json)
python3 inject.py     # tone-rubric failure injection
python3 try_its.py    # critique dropped; Spanish replies; days_between tool
python3 new_run/tests/test_budget_guard.py
python3 new_run/tests/test_agent_budget_multiturn_offline.py
```

The commands above reproduce the chapter from the cached run without any API calls; keep `budget_ledger.json` as it is if you want the cost figures to stay comparable. The historical `./run_all.sh` → `OUTPUT.txt` path remains a legacy harness only.

## Models and assumed prices

In prose the chapter says "a small fast model" and "a larger one from the same provider". Identifiers, used here and in figure captions only:

| Role in the lab | Identifier | Assumed list price (US dollars per million tokens, in / out) |
|---|---|---|
| Small judge and reply writer | `claude-haiku-4-5-20251001` | $1 / $5 |
| Large judge and large agent | `claude-sonnet-4-5-20250929` | $3 / $15 |

Prices are illustrative assumptions recorded on 1 November 2026; they are not a vendor quote. A run against another model family is marked [RESULT PENDING] in the book.

## Fixture (SIMULATED)

- Fortnight Monday 4 to Sunday 17 October 2027. All-flow IDs `t-177401` to `t-185250`. Fee conversations: 1,640 (`t-177402` to `t-185242`).
- Policy: fee-schedule-2026-03; late fee $25 after 15 days; one courtesy waiver in twelve months for borrowers on autopay.
- Kinds and MC-02 v1.1 labels are planted. Reply text is written later from a brief, so truth comes from the kind.
- `tool_bug` (candidate FM-27): from Monday 11 October, fee-tool 3.4 counts a courtesy waiver twelve to thirteen months back as inside the window. The reply matches the tool (pass under v1.1, fail for the borrower). Chapter 15 already used FM-26 for a stated change of work; this chapter does not reuse the code.
- Judge eval set `fee-judge-v1`: 150 at random plus 150 targeted, split 100 dev / 200 test, stratified by kind.
- Agent study: 20 `tool_bug` traces (none from dev) and 40 other test traces.

## NEW REAL run (`ch16-full-new-2026-11-08-2131`)

Caches live under `new_run/ch16-full-new-2026-11-08-2131/out/`: `judge.jsonl` (2476 digest rows; 2480 planned judge jobs / 2476 unique legit shared-bug test jobs), agent `agent_*.jsonl` (180 traces), replies / alt / spanish. Ledger charged **$6.191862** + unreconciled **$0.050079** + headroom **$0.05** → safe ceiling **$6.291941** under the original $12 cap. Jsonl rows **3154 ≠** API creates; final `request_id`s **3391**; agent turns **417**; ledger commits **3396**; orphans **5**. Full request-cost report is cost authority; actual billing is not claimed from an invoice.

Primary held-out small v1 r0: **TPR 52/52, TNR 147/148, κ 0.987** (1 FP `t-178668`). Flips **1/200**. Pairwise contrast **37/1/2**. Agents bugs **9/20**, **19/20**, **18/20**. Admit: **order True**, **decide False** (`role decide needs a Judge Report Card`) — not production decide approval.

## Failure injection

`p_tone` in `judges.py` replaces the MC-02 rules with "clear, polite, empathetic and helpful". On the same 200 test traces the facts judge is TPR 1.000 / TNR 0.993; the tone rubric is TPR 0.981 / TNR 0.534 (kappa 0.363). It does not let warm-and-wrong replies through (0 of 30); it over-flags correct replies (68 of 148 fail under tone, plus slices 36/77 warm-right and 32/71 curt-right).

## Try-it-yourself

1. Verdict only, no critique: TPR 51/52, TNR 140/148 (kappa 0.888).
2. Same rules on 100 Spanish translations (prompt still in English): TPR 29/29, TNR 71/71, matching English.
3. Small agent plus a `days_between` calculator: bugs caught 9/20 → 18/20; five false alarms on the other 40; the calculator used on 57 of 60 traces.

## Truss

Package 0.19.0, module `truss.judge`, called Truss v3 in the book. Seven tests in `04-code/truss/tests/test_ch16.py`. The full suite is 105 passing tests at the end of this chapter.
