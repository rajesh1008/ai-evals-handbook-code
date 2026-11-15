# Offline report correction — 2026-11-08 ~23:50 Asia/Calcutta

Triggered by an independent audit of the first aggregate report.

## Changes
1. Archived prior `NEW_RESULTS.*` → `reports/superseded_2026-11-08-bad-aggregate/` (aggregate.score_exp abstain bug + incomplete tables).
2. Regenerated metrics via official `python3 lab.py` with `CH16_OUT` → this run’s raw caches (authority: `common.score`).
3. Wrote corrected `NEW_RESULTS.md` / `NEW_RESULTS.json` / `NEW_METRICS_PROVENANCE.json` with kappa, Wilson CI, flips, pairwise, agents, cost accounting.
4. Clarified **3154 jsonl rows ≠ API requests**; documented request_id / ledger orphan accounting.
5. Added `new_run/tests/test_agent_budget_multiturn_offline.py` (2 offline mocks). Prior 11 budget tests still pass.

## Non-changes
- No paid API. Ledger not reset. Unreconciled $0.050079 retained.
- modest_* / historical OUTPUT.txt SHA unchanged.
