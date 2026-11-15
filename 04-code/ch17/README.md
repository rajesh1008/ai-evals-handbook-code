# Chapter 17 lab: the bias battery

Three SIMULATED judges (`judges.py`) score 200 planted fee-explanation pairs
(`fixture.py`, seed 2026, pair IDs p-0001 to p-0200). No live model is called.
Truss computations (`truss.bias`) are real.

- `lab.py` — position, verbosity, self-preference, authorship labels, authority
  cue, rubric anchoring, segment gaps, the battery, and a three-judge panel.
- `inject.py` — a gold-following judge plus 18 forced first-slot pairs (9.0%).
- `try_its.py` — 50% pad; close+tied only; same-family vs mixed panel.
- `real_judge.py` — records a pending live three-model run.

```
./run_all.sh
```

Judge identifiers (`S`, `L`, `X`) stay out of the chapter prose: the small
same-family stand-in for fee-judge-v1, a larger model from the same provider,
and a model from a second provider.
