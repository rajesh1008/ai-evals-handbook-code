# Chapter 5 Lab: Error Analysis

Truss v0.8. Harbor Lending and Compass are fictional. The Lab reads Chapter 2's December
store (`../ch02/out/harbor.db`, built by `../ch02/run_all.sh`) and draws a fresh, risk-weighted
sample of 150 traces from it on Tue 15 Dec 2026, excluding the 314 traces already read in
Chapters 2 to 4 (the first pass and the gate sample share their 300 IDs) and the 14 complaints.

Stated assumptions, so nobody mistakes the fixture for a finding:

- **Who reads.** Reading is simulated: `reading.py` plants a cause on each failing trace from the
  store's own truth table and writes a one-sentence note from a fixed set of wordings per cause.
  Passing traces get a short pass note 12% of the time. Reading minutes per flow are planted
  (`MINUTES`); Chapter 2 measured 9 to 14 minutes for hardship traces.
- **Chapter 2's first pass.** The 27 failing first-pass notes from `../ch02/out/first_pass.csv`
  are used as text only. The Chapter 2 labels were written against a separate fiction, so the
  Lab never compares them with this store's spans; trajectory and hypothesis checks use only the
  December sample and the complaints.
- **Second coder.** Ben Fletcher (hardship) and Ryan Mitchell (other flows) code the 53 failing
  traces blind to the notes. Their planted differences are listed in `reading.SECOND`.
- **Semantic search.** `truss.coding.Index` is a lexical TF-IDF index over character n-grams and
  words. It stands in for an embedding model; pass `embed=` to use a real one. The precision
  numbers describe the stand-in, not any embedding model.

Run everything: `./run_all.sh` (about two minutes, most of it in `try_its.py`; writes `OUTPUT.txt`,
then runs the Truss tests).

| Step | File | What it shows |
|---|---|---|
| A | `lab.py` | The December draw: frame, weights, quotas, failures found by flow |
| B | `lab.py` | Open coding: pooled notes from three sources, the note lint |
| C | `lab.py`, `codebook.py` | Suggested groups, axial decisions, twelve clusters then thirteen, counts by source |
| D | `lab.py` | Saturation curve and the per-flow detection floor |
| E | `lab.py` | Hours and cost of the reading |
| F | `lab.py` | Second coding, Cohen's kappa, disagreements by kind |
| G | `lab.py` | Three hypotheses and their tests (H1 against the full December retrieval census) |
| H | `lab.py` | First wrong step in each failing December trajectory |
| I | `lab.py` | Searching notes and complaints by meaning |
| J | `lab.py` | Taxonomy v0.1 written to `out/taxonomy-v0.1.md` |
| Injection | `inject.py` | A second annotator with a narrower definition of a wrong fee explanation |
| Try it | `try_its.py` | Uniform against risk-weighted draws; reading 75 to 600; reading order |

New Truss module: `truss/coding.py` (`OpenCode`, `note_problems`, `Index`, `jaccard_search`,
`precision_at_k`, `suggest_groups`, `purity`, `Category`, `axial`, `saturation_curve`, `last_new`,
`detect_prob`, `detectable_rate`, `cohen_kappa`, `confusion`, `first_wrong_step`, `Hypothesis`,
`codebook_markdown`); tests in `../truss/tests/test_ch05.py`.

Model-assisted coding (`model_coding.py`) was run for real on 1 Nov 2026 against
`claude-haiku-4-5-20251001` and `claude-sonnet-4-6` at temperature 0. The raw responses are cached
in `out/model/`, so `run_all.sh` reproduces the numbers without a key; `python3 model_coding.py
--live` calls the API again (needs `ANTHROPIC_API_KEY`). The notes it reads come from a small set
of planted wordings, so its scores are a ceiling for clean notes, not a forecast for messy ones.
