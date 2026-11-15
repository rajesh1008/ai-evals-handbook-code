# Chapter 1 Lab: run Compass on 20 conversations, three times

Compass is fictional, so `compass_sim.py` stands in for it. It is seeded (2026
for sampling, SHA-256 of the trace ID and run for replies) so every number in
the chapter reproduces. To try a real model, replace `respond()` with a call
to your own client; nothing else changes.

The difficulty parameters in `FLOW_DIFFICULTY` were set once, before the first
run, and were not tuned to produce any particular flip rate.

| Script | What it shows |
|---|---|
| `lab.py` | 20 conversations, three runs at the production temperature 0.7 |
| `inject_failure.py` | Failure injection: a leftover `COMPASS_TEMPERATURE=0` hides the variance until run 3 |
| `try_temperature.py` | Try it yourself 1: flip rate at temperature 0, 0.3, 0.7, 1.0 |
| `try_ten_runs.py` | Try it yourself 2: ten runs, pass@k against pass^k |
| `try_ryan_sheet.py` | Try it yourself 3: replay Ryan's 40 conversations |

Run `./run_all.sh` to regenerate `OUTPUT.txt`. Needs the pilot store built by
`../truss/fixtures/make_fixture.py`. Tests live in `../truss/tests/test_ch01_lab.py`.
