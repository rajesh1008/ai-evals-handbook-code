# Chapter 23 lab — Evaluating Retrieval and Grounding

Measures Compass's policy retrieval separately from answer generation.

- `corpus.py` — Harbor policy chunks (live + retired fee schedule).
- `fixture.py` — SIMULATED gold queries, rankings, production cases (seed 2026).
- `lab.py` — recall@k / MRR / nDCG, groundedness, chunking, synthetic filter, embeddings.
- `inject.py` — stale index with fee-schedule-2024-01 still retrievable.
- `try_its.py` — three variations.
- `real_grounding.py` — modest live Anthropic groundedness judgements.

```bash
./run_all.sh
python3 real_grounding.py run   # optional; needs ANTHROPIC_API_KEY
```

Truss: `truss.retrieval` (0.26 docstring line; package `__version__` is 0.27.0 from Chapter 24).
