# Chapter 12 Lab: datasets, golden, synthetic and alive

Run `./run_all.sh` (no API key needed: the two real model runs are cached in `out/`). It writes `OUTPUT.txt`.

| File | What it does | Real or simulated |
|---|---|---|
| `policy.py` | HP-2027-04 first-reply rules as code (`decide`), the ground truth for synthetic cases | code |
| `synth.py` | 40 calls to `claude-haiku-4-5-20251001`, persona x reason grid, ten cases each: 400 synthetic hardship cases (`out/synth_raw.jsonl`) | **real model run** |
| `validate.py` | parse, schema, internal consistency, label check against `policy.decide`, near-duplicates; writes `out/synth_cases.json`, `out/validate.json` | real data, code checks |
| `leak.py` | failure injection: 80 admitted synthetic cases decided by the same small model with two retrieved worked examples; in the leaked run, 40 test cases sit in the knowledge base with their answers; then the 8-word-shingle and canary scan (`out/leak.jsonl`, `out/leak.json`) | **real model run** (160 calls) |
| `golden.py` | golden set v1.0 fixture (1,200 cases) and the book's simulator of Compass verdicts | **SIMULATED** (planted rates, seed 2026; production hardship turn counts from the pilot DB) |
| `lab.py` | manifest and composition, authored vs production vs synthetic, slice sensitivity, slice-by-slice gate, dev-split tuning simulation, v1.0 to v1.1 audit and diff, regression and progression sets, five properties | mixes: says which on every section |
| `inject.py` | prints the leak injection and its detection | real |
| `try_its.py` | three variations: dedupe threshold, generator labels vs policy labels, enriched slices | real data / arithmetic |

Truss module: `../truss/truss/datasets.py` (Truss 0.15.0, "Truss v2"), tests in `../truss/tests/test_ch12.py`.

To redo the model runs (Anthropic key in `ANTHROPIC_API_KEY`, never printed): delete the caches, then
`python3 synth.py run && python3 validate.py && python3 leak.py run && ./run_all.sh`. A rerun will give different
cases and slightly different counts; the chapter quotes the cached run.
