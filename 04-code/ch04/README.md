# Chapter 4 Lab: The Test Pyramid for AI Systems

Truss v0.7. Harbor Lending and Compass are fictional. The Lab reads the Chapter 3
v0.5 trace store (`../ch03/out/trace_store.db`, rebuilt from seed 2026 if missing).
Token prices, run frequencies and CI runner rates are stated assumptions in
`harbor.py` (`PRICES`, `RUNS_PER_MONTH`); change them to yours.

Run everything: `./run_all.sh` (about 15 seconds; writes `OUTPUT.txt`, then runs the Truss tests).

| Step | File | What it shows |
|---|---|---|
| A | `lab.py` | Every check Harbor Lending runs, tagged with layer, stream, stages and owner; checks per layer before and after |
| B | `lab.py` | First run in the pilot state: the layer-one index check holds every stage on the retired 2024 fee schedule |
| C | `lab.py` | The three fee complaints traced to the retired document; 336 pilot traces retrieved it |
| D | `lab.py` | Cost per release by layer, the shadow week, weekly monitoring, and the monthly bill by layer |
| E | `lab.py` | One defect injected per layer; the first layer that catches each and what was spent to get there |
| Injection | `inject.py` | A layer-three judge wired into the commit hook: the lint, the bill, the wall time, 38 of 40 false holds |
| Try it | `try_its.py` | Place a check of your own; change stage frequencies; delete layer two and watch the router defect move up |

New Truss module: `truss/layers.py` (`Check`, `Cost`, `Suite`, `lint`, `monthly_bill`, `summarise`);
tests in `../truss/tests/test_ch04.py`. Stand-in components with switchable defects: `harbor.py`.
The full suite: `suite.py`.
