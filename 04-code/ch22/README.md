# Chapter 22 lab: judging the judge's explanations

Does a judge's written critique tell you when its verdict is wrong? Traffic and planted truth are
SIMULATED (`fixture.py`, seed 2026): 300 fee-explanation traces from Monday 31 January to Sunday
27 February 2028 (IDs `t-245206` to `t-261196`, all ending in 6, clear of Chapter 20's hardship
IDs), 120 drawn at random from the weekly fresh gold and 180 targeted, split 100 development /
200 held-out by kind. Reply text, every judge verdict and critique, and the two rationale readers
are REAL model runs cached under `out/` (3,800 calls including the 300 replies), so the analyses
rerun without a key.

## The study judge

Production fee-judge-v2 reads the fee tool's waiver status. The study judge reads the account
history instead and must work out the twelve-month window itself, the input a history-reading fee
judge would need after Chapter 16's tool bug. Its rules are in `judges.py` (`RULES`), written over
four drafts on the development set only (`r1`, `r1b_dev`, `r2_dev`, `v2_dev`); the run of record is
`v2` on all 300. The draft-3 worked example ("fee date 2028-02-09 gives cut-off 2027-02-09") was
copied into 37 of 100 development critiques, which is how it was found.

## What to run

```bash
./run_all.sh            # everything below, saved as OUTPUT.txt
python3 lab.py          # validation, rationale features, flag rules, cue, cost, window input
python3 inject.py       # failure injection: the reviewer-ready prompt
python3 try_its.py      # verdict only; evidence first; two-draw disagreement
python3 judges.py run <experiment>   # recache (needs ANTHROPIC_API_KEY)
```

## Models and assumed prices

Prose says "a small fast model". Identifier, here and in figure captions only:
`claude-haiku-4-5-20251001`, assumed $1 / $5 per million tokens in / out (illustrative, as in
Chapter 16). API default sampling; the 13 flips in 100 between two plain draws are part of the result.

## Experiments (`judges.py`)

| Tag | What | Traces |
|---|---|---|
| `v2` | critique first, JSON last (study judge of record) | 300 |
| `vonly` | same rules, verdict only (Try It 1) | 300 |
| `v3` | reviewer-ready: verdict first, four-heading explanation (failure injection) | 300 |
| `proof` | evidence fields first, then verdict (Try It 2) | 200 |
| `window_in` | critique first with the code's window result as an input | 200 |
| `cue_base`, `cue` | plain repeat; authority sentence appended to the reply | 100 |
| `read_*` | rationale reader: critique only, implied verdict, grounds, convincing 1-5 | |
| `claims_*` | claim extractor: cut-off, waiver date, window, status the critique asserts | |

The feature list in `common.py` was settled after reading development critiques. One exploratory
association pass over all 300 was run before the claim extractor was written; rules are fitted on
development traces only and scored on the held-out 200.

## Truss

Package 0.25.0, module `truss.rationale`. Seven tests in `04-code/truss/tests/test_ch22.py`.

## Total spend

The cached runs of record are 3,800 calls (3,500 judge, reader and claim calls, $5.13, plus 300 replies, $0.25).
A further 900 calls ran four judge variants under the first draft of the rules and were discarded when the rules
changed; they are kept in `out/draft_r1/` for the record. All in: 4,700 calls, about $7.28 at the assumed prices of
$1 and $5 per million input and output tokens for claude-haiku-4-5-20251001.
