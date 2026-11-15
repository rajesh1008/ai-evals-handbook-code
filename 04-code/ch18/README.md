# Chapter 18 lab: Validating and Correcting Judge Estimates

Reader gold and judge verdicts are SIMULATED (`fixture.py`, seed 2026). No model
is called. The stand-in is a documented error model for fee-judge-v1 (MC-02
v1.1): it under-calls residual fee failures, more so on Spanish traces and on
window arithmetic. Truss 0.21 `reportcard` computes confusion, kappa,
Rogan-Gladen, prediction-powered inference, leak and kind-mix checks,
invariance, sensitivity, and decide-role admission on those verdicts.

```
./run_all.sh
```

Writes `out/lab.json`, `out/inject.json`, `out/try_its.json` and prints the
numbers the chapter quotes.

Failure injection (`inject.py`): a 200-trace validation set drawn from the
Chapter 16 development kind mix (the distribution of the rubric examples),
on which the stand-in is more accurate. The card refuses admission because
the kind-mix clones the reserved set.

Try It 1: human-only interval width as the labelled set grows.
Try It 2: PPI on 200 labels vs 300.
Try It 3: the error of publishing the raw judge rate against the planted truth.
