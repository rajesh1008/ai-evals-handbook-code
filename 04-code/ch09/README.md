# Chapter 9 lab: code-based checks

Truss 0.12 adds `truss.checks` (verifiers, composition, schema subset, money and date extraction,
day-count conventions, calendar-month windows, validation helpers).

| File | What it does |
|---|---|
| `april.py` | Fixture for Thu 1 to Wed 14 April 2027: 8,096 conversations, t-100099 to t-108194, seed 2028. Like February and March, the fixture generates only the first fortnight of each month, so there are no traces for 15 to 31 March. Adds account records (loan IDs, products, nicknames, principal, APR, day count, relief history), a policy corpus (FS-2026-02, HP-2026-09, HP-2027-04, PL-2026-01), the payoff tool's Sunday-interest defect, Spanish approval wording and two release candidates (rc-0412-1, rc-0414-2). |
| `compass_checks.py` | The eight checks C-01 to C-08 and `suite()`. |
| `lab.py` | Sections A to K; writes `out/lab.json`. |
| `inject.py` | C-07 with the day-count convention hard-coded (30/360, actual/365) against reading it from the loan record. |
| `try_its.py` | Nicknames in C-02, the negation rule in C-06, the leap-year window. |
| `judge_vs_code.py` | Real run: claude-haiku-4-5-20251001, each prompt twice, 220 calls, cached in `out/judge_vs_code.jsonl`. `python3 judge_vs_code.py run` calls the API with `ANTHROPIC_API_KEY` from the environment; without `run` it reads the cache. |
| `run_all.sh` | Runs everything into `OUTPUT.txt`, then the Truss tests. |

Reader judgements in the validation section are the fixture's planted truth, standing in for the people who
read the flags and the sample; the chapter says so where it uses them.
