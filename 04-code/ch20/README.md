# Chapter 20 lab: confidence, calibration and routing

Run everything with `bash run_all.sh` (Python 3, standard library plus the repository's Truss package). Output is in `OUTPUT.txt`; machine-readable results are in `out/*.json`, which the figure scripts in `03-figures/src/ch20/` read.

**SIMULATED.** Every hardship decision, its gold correctness, the three confidence fields (verbalised, action-token probability, judge-estimated), the officers' catch and slip rates, the overload effect, the four live weeks, the model change on 14 February 2028, the recalibration draw and the constant-confidence injection are planted by `fixture.py` (seed 2026). The planted rates are in the fixture's docstring. No model is called by any script here.

**REAL.** Every statistic is computed by `truss.calibration` (Truss 0.23, the book's Truss v3.5): reliability tables, ECE, MCE, Brier score and decomposition, AUROC, the degenerate-field check, logistic and isotonic recalibration maps bound to a model pin and a policy digest, conformal risk control and exact-bound thresholds, the feasibility floor, the fail-closed route rule, the routing simulator and the stratified post-review estimate. Tests: `cd ../truss && python3 -m pytest -q tests/test_ch20.py` (7 tests).

**PENDING.** `real_confidence.py` asks a real decision step for its action and a stated confidence on Chapter 15's 160 authored cases (`from probe import cases`) and records action-token probabilities where the provider returns them. No provider client is wired and no API key exists, so it prints `[RESULT PENDING: run cd 04-code/ch20 && python3 real_confidence.py run after a provider client is wired]`. The book marks it [RESULT PENDING].

| Script | What it prints |
|---|---|
| `lab.py` | Sections 1 to 11: sets, citations, three fields, segments, the map, thresholds, five policies on January, load at three traffic levels, live weeks, model change, costs |
| `inject.py` | The constant 1.0 injection with and without the degenerate guard |
| `try_its.py` | The three Try It Yourself variations (ECE protocols, routing on verbalised, routing on judge-estimated) |
| `listings.py` | The code listings printed in the chapter and their outputs, plus the threshold sweeps and small counts quoted in the text |
| `real_confidence.py` | The pending live run (prints the marker) |

Version note: Chapter 20 reserved Truss 0.23.0 for `calibration`; Chapter 21, written in parallel, ships 0.24.0 `trial`, so `truss.__version__` reads 0.24.0 and the package docstring carries both lines. The full suite is 140 tests.

Illustrative prices: officer time $60 an hour; a final label $13.90 (Chapter 14); judge calls at the Chapter 16 small-model price.
