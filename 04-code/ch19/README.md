# Chapter 19 lab: keeping judges honest

SIMULATED judges and gold (`fixture.py`, seed 2026) produce six weekly
canaries of 100 traces (40 frozen + 60 fresh) and a 200-trace
revalidation set. No live model is called. Truss computations
(`truss.drift`) are real.

- `lab.py` — weekly two-track reports, alerts, version digests, the
  change-control gate, and revalidation of fee-judge-v2.
- `inject.py` — HB-2027-12 takes effect and the judge is still v1;
  agreement falls to 0.62; a Monday-morning update is the counterfactual.
- `try_its.py` — frozen-only monitoring; a silent model swap; a rubric
  wording change versus that swap.
- `real_judge.py` — records a pending live run (frozen canary, three
  repeats, temperature 0).

```
./run_all.sh
```

Model identifiers stay out of the chapter prose. The production names
are fee-judge-v1 and fee-judge-v2. The frozen canary uses t-184901 to
t-184940 so a parallel Chapter 18 writer can take t-185251 upward.
