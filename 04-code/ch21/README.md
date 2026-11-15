# Chapter 21 lab: a judge fails its trial

SIMULATED officer gold and judge verdicts (`fixture.py`, seed 2026) for 100
development and 200 held-out hardship offers. No live model is called. Truss
computations (`truss.trial`, 0.24.0; `truss.judge`, 0.19) are real.

- `lab.py`: hardship-judge-v1's development score and held-out validation
  table, admission, disagreements by cause, the surface check, the
  construct-validity profile, the escape bound against Victor's 0.5%, and
  the fix (hardship-judge-v2) with the leak guard.
- `inject.py`: the failure injection. The judge is split into
  stated-change-judge-v1 (reads what the borrower said) and
  permission-judge-v1 (decides, with C-02, C-03 and C-09 results as inputs).
  Part A clears the floors; part B still fails. Decision record.
- `try_its.py`: random-only trial; C-03 result as an input; a panel of three.
- `real_judge.py`: records the pending live run.

```
./run_all.sh
```

Trace IDs are hardship offers between t-185253 and t-229198 ending in 3 or 8,
clear of Chapter 18's census, Chapter 19's canaries and revalidation set, and
the parallel Chapter 20 writer. Model identifiers stay out of the chapter
prose; the stand-in is "the larger model from the same family" as fee-judge-v1.
