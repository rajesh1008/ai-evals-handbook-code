# Chapter 16 FULL NEW experiment — ch16-full-new-2026-11-08-2131

**NOT** a recovery of missing historical caches. NEW Anthropic replication under a hard **US$12** global cap.

- Started: 2026-11-08 ~21:31 Asia/Calcutta.
- Models ONLY: `claude-haiku-4-5-20251001` ($1/$5), `claude-sonnet-4-5-20250929` ($3/$15).
- Fixtures/prompts/pins: unchanged (`fixture.py` seed 2026; gen/judges/agent prompt functions).
- Budget: `budget.py` atomic ledger — reserve worst-case before every `messages.create`; SDK `max_retries=0`.
- Outputs: **this directory only**. Does **not** overwrite `04-code/ch16/out/modest_*`, historical `OUTPUT.txt`, or missing-cache evidence.
- This is the run Chapter 16 reports. Re-running `run_full.py` places new paid API calls; the offline commands in `ch16/README.md` do not.

## Reproduce

```bash
cd 04-code/ch16
python3 new_run/tests/test_budget_guard.py   # must PASS before paid calls
export CH16_RUN_ID=ch16-full-new-2026-11-08-2131
export CH16_OUT=$(pwd)/new_run/ch16-full-new-2026-11-08-2131/out
export CH16_BUDGET_LEDGER=$(pwd)/new_run/ch16-full-new-2026-11-08-2131/budget_ledger.json
export CH16_BUDGET_CAP=12
export CH16_BUDGET_HEADROOM=0.05
# ANTHROPIC_API_KEY must already be in the environment (never print)
python3 new_run/ch16-full-new-2026-11-08-2131/run_full.py
```

## Stages
1. gen.py → replies / alt_replies / spanish (~498)
2. judges.py → judge.jsonl (2480)
3. agent.py → agent_small / agent_large / agent_small_calc (60×3)
4. aggregate report from raw jsonl + ledger
