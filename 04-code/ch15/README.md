# Chapter 15 lab: the metric suite for the hardship flow

The September traffic, the gold replay and every officer reading are **simulated**: `fixture.py`
builds 480 hardship conversations (6 to 19 September 2027, t-161626 to t-169472) and the 654 gold
labels (299 from hardship-gold v1.0 in Chapter 13, 295 regenerated for the Chapter 14 weeks of 2 August
to 3 September, 60 from the week of 6 September). The production build's errors are planted at stated
rates. The code checks, the composition audit, the gate arithmetic and the bounds are real computations
on that data. The prompt experiment in `probe.py` is **real**: claude-haiku-4-5-20251001, default
sampling (this SDK version takes no temperature argument), every prompt run twice, cached in `out/`.

| File | What it does |
|---|---|
| `fixture.py` | SIMULATED frame and gold, segments and overlapping flags, policy (HP-2027-04 with HB-2027-07) |
| `probe.py` | REAL: 160 authored facts-first cases in eight segments, four prompts, two runs each (1,280 calls) |
| `lab.py` | A flow map; B taxonomy of the replay; C census by code checks (C-03 v1.0 and v1.1, C-09); D composition audit; E decision table and the two-way gate on the real probe; F Victor's arithmetic |
| `inject.py` | failure injection: a documented-income-only gate set ships a SIMULATED candidate (rc-0920-1) that the full gold holds |
| `try_its.py` | audit thresholds; one-direction and accuracy-only gates on the real probe; weeks to a bound |

Run: `./run_all.sh` (cached), or `./run_all.sh run` to call the model for anything uncached.
Truss 0.18.0 (`truss/flowsuite.py`, `checks.within_months(anniversary_inside=False)`, tests in `truss/tests/test_ch15.py`).
Tokens: probe 851,952 input / 61,343 output.
Pending: the same probe on a second model family (marked [RESULT PENDING] in the book); it needs a second client in `call()` and its own cache key.
The real probe did **not** reproduce the self-employed regression; `inject.py` plants it.
