# NEW Ch16 results — ch16-full-new-2026-11-08-2131 (corrected)

**NEW Anthropic experiment — NOT recovered historical.**
Fixture labels: **SIMULATED** (`fixture.py` seed 2026). Reply / judge / agent texts: **REAL** Anthropic caches under this run id.

Supersedes `reports/superseded_2026-11-08-bad-aggregate/` (wrong abstain math + incomplete tables).

Scoring authority: `common.score` → `truss.judge` (**abstain counts in TPR/TNR denominators**). Wilson CIs are per-trace Bernoulli on the labelled set — **not** treating multi-turn agent calls as independent trials.

## Budget / API accounting

| Field | Value |
|---|---:|
| Cap | $12.00 |
| Ledger charged | $6.191862 |
| Unreconciled held (8 hung judge) | $0.050079 |
| Headroom | $0.05 |
| **Safe ceiling** | **$6.291941** |
| Jsonl rows (498 gen + 2476 judge digests + 180 agent **traces**) | 3154 |
| Unique Anthropic `request_id`s in final caches | 3391 |
| Agent turns (sum `request_ids`) | 417 |
| Ledger committed entries | 3396 |
| Orphans (committed − final request_ids) | 5 |

**3154 is jsonl rows, not Messages API creates.** Agent multi-turn + 5 orphaned timeout commits explain ledger 3396 vs final ids ~3391.
Unreconciled $0.05 stays charged-against-cap (cannot prove uncharged).

## Judges (common.score)

| Experiment | n | TPR (Wilson) | TNR (Wilson) | kappa | abstain | cm |
|---|---:|---|---|---:|---:|---|
| test_j0 | 200 | 0/52 = 0.000 (0.000–0.069) | 3/148 = 0.020 (0.007–0.058) | 0.004 | 197 | `{'tp': 0, 'fn': 0, 'fp': 0, 'tn': 3, 'abstain_pos': 52, 'abstain_neg': 145}` |
| test_v0 | 200 | 37/52 = 0.712 (0.577–0.817) | 104/148 = 0.703 (0.625–0.770) | 0.423 | 16 | `{'tp': 37, 'fn': 0, 'fp': 43, 'tn': 104, 'abstain_pos': 15, 'abstain_neg': 1}` |
| test_v1_small_r0 | 200 | 52/52 = 1.000 (0.931–1.000) | 147/148 = 0.993 (0.963–0.999) | 0.987 | 0 | `{'tp': 52, 'fn': 0, 'fp': 1, 'tn': 147, 'abstain_pos': 0, 'abstain_neg': 0}` |
| test_v1_small_r1 | 200 | 52/52 = 1.000 (0.931–1.000) | 148/148 = 1.000 (0.975–1.000) | 1.000 | 0 | `{'tp': 52, 'fn': 0, 'fp': 0, 'tn': 148, 'abstain_pos': 0, 'abstain_neg': 0}` |
| test_v1_small_r2 | 200 | 52/52 = 1.000 (0.931–1.000) | 147/148 = 0.993 (0.963–0.999) | 0.987 | 0 | `{'tp': 52, 'fn': 0, 'fp': 1, 'tn': 147, 'abstain_pos': 0, 'abstain_neg': 0}` |
| test_v1_large | 200 | 52/52 = 1.000 (0.931–1.000) | 147/148 = 0.993 (0.963–0.999) | 0.987 | 0 | `{'tp': 52, 'fn': 0, 'fp': 1, 'tn': 147, 'abstain_pos': 0, 'abstain_neg': 0}` |
| test_v1_think | 200 | 52/52 = 1.000 (0.931–1.000) | 148/148 = 1.000 (0.975–1.000) | 1.000 | 0 | `{'tp': 52, 'fn': 0, 'fp': 0, 'tn': 148, 'abstain_pos': 0, 'abstain_neg': 0}` |
| test_verdict_only | 200 | 51/52 = 0.981 (0.899–0.997) | 140/148 = 0.946 (0.897–0.972) | 0.888 | 0 | `{'tp': 51, 'fn': 1, 'fp': 8, 'tn': 140, 'abstain_pos': 0, 'abstain_neg': 0}` |
| test_tone | 200 | 51/52 = 0.981 (0.899–0.997) | 79/148 = 0.534 (0.454–0.612) | 0.363 | 1 | `{'tp': 51, 'fn': 1, 'fp': 68, 'tn': 79, 'abstain_pos': 0, 'abstain_neg': 1}` |
| test_v1_spanish | 100 | 29/29 = 1.000 (0.883–1.000) | 71/71 = 1.000 (0.949–1.000) | 1.000 | 0 | `{'tp': 29, 'fn': 0, 'fp': 0, 'tn': 71, 'abstain_pos': 0, 'abstain_neg': 0}` |

Flips across 3 small-v1 repeats: **1** of 200 — where: ['t-178668']

### Pairwise
- Contrast (n=40): {'position': 2, 'right reply preferred': 37, 'wrong reply preferred': 1}
- Equal length (n=40): {'position': 18, 'longer preferred': 21, 'shorter preferred': 1}
- Absolute v1 both-right: contrast 40/40, equal 40/40

### Admission
- order: {'admit': True, 'role': 'order', 'card': 'MC-02 v1.1', 'reasons': []}
- decide: {'admit': False, 'role': 'none', 'card': 'MC-02 v1.1', 'reasons': ['role decide needs a Judge Report Card']}

## Agents (truth label; tool_bug catch = bugs TPR numerator)
| Variant | tool_bug | bugs TPR | normal TPR | normal TNR | kappa | cost/trace | p50 s | tool calls |
|---|---:|---|---|---|---:|---:|---:|---|
| agent small | 9/20 | 9/20=0.450 | 13/13=1.000 (0.772–1.000) | 23/27=0.852 (0.675–0.941) | 0.789 | $0.0051 | 5.6 | {'2': 60} |
| agent large | 19/20 | 19/20=0.950 | 13/13=1.000 (0.772–1.000) | 25/27=0.926 (0.766–0.979) | 0.890 | $0.0161 | 10.9 | {'2': 60} |
| agent small + days_between | 18/20 | 18/20=0.900 | 13/13=1.000 (0.772–1.000) | 22/27=0.815 (0.633–0.918) | 0.741 | $0.0068 | 5.9 | {'3': 57, '2': 3} |

## Cost by family (unique jsonl token reprice)

- `agent_large`: 60 rows, in 157,494 out 32,926, ~$0.9664
- `agent_small`: 60 rows, in 157,384 out 29,340, ~$0.3041
- `agent_small_calc`: 60 rows, in 263,005 out 29,223, ~$0.4091
- `alt_replies`: 80 rows, in 15,827 out 14,760, ~$0.0896
- `judge`: 2476 rows, in 1,458,020 out 394,587, ~$4.0198
- `replies`: 318 rows, in 64,012 out 41,125, ~$0.2696
- `spanish`: 100 rows, in 19,544 out 21,003, ~$0.1246
- **Sum unique-row token cost:** $6.183180 (ledger charged $6.191862; gap includes orphaned commits / rounding)

## Explicit non-claims

- Not a recovery of missing historical caches.
- Numbers may differ from historical `OUTPUT.txt` (and do, e.g. v1 TNR 147/148, agent_small bugs 9/20).

## Reproduce (offline)
```bash
cd 04-code/ch16
export CH16_OUT=$PWD/new_run/ch16-full-new-2026-11-08-2131/out
python3 lab.py > new_run/ch16-full-new-2026-11-08-2131/reports/lab_NEW_stdout.txt
python3 new_run/tests/test_budget_guard.py
python3 new_run/tests/test_agent_budget_multiturn_offline.py
```
