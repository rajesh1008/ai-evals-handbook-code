# Chapter 25 lab — Simulated Users and Multi-Turn Evaluation

- `fixture.py` — 300 SIMULATED hardship conversations (seed 2026, digests) plus 100 real-transcript summary rows (no PII).
- `lab.py` — goal completion, abandonment, persona table, fidelity vs real, perturbation survival.
- `inject.py` — polite_deferrer persona never pushes back; 20 hidden wrong offers pass outcome-only scoring.
- `try_its.py` — drop polite cohort; min pushback filter; short vs long strata.
- `real_sim.py` — modest REAL Anthropic fidelity labels (`--live`); cached in `out/real_sim.json`.
- Truss 0.28 `simuser`.

Run: `./run_all.sh` or `./run_all.sh --live`.
