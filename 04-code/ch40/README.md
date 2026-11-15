# Chapter 40 lab — The Weekly Report

SIMULATED weekly series (seed 2040, digest `826ca96a1c3c`). No paid API.

```bash
bash run_all.sh
PYTHONPATH=../truss python3 -m pytest -q ../truss/tests/test_weeklyreport.py
```

Failure injection: overall trend hides hardship segment regression (`caught=true`).
