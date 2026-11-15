# Chapter 2 Lab: a first honest evaluation, end to end

Run `./run_all.sh`. It writes `OUTPUT.txt` (the output quoted in the chapter)
and `out/*.json` (the data the Chapter 2 figures are drawn from), then runs
the Truss tests.

| Script | What it does |
|---|---|
| `lab.py` | Ryan's sheet against the pilot; the 300-trace stratified sample; completeness check; two traces through the labeller CLI; the first report; a second reader on 20 hardship traces |
| `inject.py` | Failure injection: a logging bug drops tool calls from about 10% of traces; labels with and without the completeness check |
| `gate_run.py` | Gate v0 on a candidate that adds generic "best practice" lines to the prompt |
| `monitor.py` | Four weeks of weekly monitoring samples, the logging bug in week 3, the hardship evidence count |
| `try_its.py` | The three Try It Yourself variations |
| `pilot_detail.py` | Fixture detail the Chapter 1 trace table lacks: tool calls, first-pass labels, CLI renderings |

New Truss v0 modules (in `../truss/truss/`): `rates.py`, `complete.py`,
`label.py` (the annotator CLI), `report.py`, `gate.py`. Tests:
`../truss/tests/test_ch02.py`.

## What is synthetic

Harbor Lending, Compass and every trace are fictional. The per-flow failure
counts in the first pass (273 of 300 pass; no wrong hardship offer) were fixed
when the book was planned; which traces fail and with which note is drawn
from seed 2026. The candidate's effects in `gate_run.py` are stated
probabilities. Monitoring verdicts are drawn from the first-pass per-flow
rates; the week-3 logging bug and the week-4 wrong offer are scripted events.
The evaluation lead's spot check of Ryan's labels (lab step 7) is scripted to
record the same verdicts Ryan gave.
The shared fixture `../truss/fixtures/compass_pilot.db` is read, never written.
