# Chapter 29 lab — Evals That Survive Change

SIMULATED fixture (`seed=2029`, n=200) for Harbor's first hardship model upgrade through Truss. Failure injection: silent `loan_id`→`account_id` schema change that keeps text metrics green. Modest REAL Anthropic sample via `real_upgrade.py` when `ANTHROPIC_API_KEY` is set; otherwise clearly labelled SIMULATED stand-in.

```bash
./run_all.sh
```

Outputs land in `out/`. Plant regression: `t-320118`.
