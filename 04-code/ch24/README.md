# Chapter 24 lab: Evaluating Agent Trajectories

SIMULATED hardship trajectories (seed 2026, 500 traces t-270001–t-270500).
Truss 0.27.0 `trajectory` (Truss v4).

```bash
./run_all.sh          # fixture, lab, inject, try-its; judge from cache
./run_all.sh --live   # also run modest Anthropic trajectory judge (40 calls)
```

Failure injection: `lucky` kind reaches the right offer via `compute_plan` with guessed
arguments, skipping policy and eligibility. Outcome-only scoring passes; process scoring fails.

Judge: claude-haiku-4-5-20251001, temperature 0, 40 stratified trajectories. Cached in `out/judge/`.
