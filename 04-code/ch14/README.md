# Chapter 14 lab: annotation as an operation

The three annotators are **simulated**. No person labelled these traces: `annotators.py` generates
Marisol's, Daniel's and Kevin's labels, minutes and slips from the rules in its docstring, and `lab.py`
plays the adjudicator (98% of rulings right) and the auditor. The agreement, cost, debt and sampling
statistics are real computations on those simulated labels. The pre-label model is a **real** run of
claude-haiku-4-5-20251001 (default sampling; the installed SDK takes no temperature argument), cached in `out/`.

| File | Real or simulated | What it does |
|---|---|---|
| `fixture.py` | simulated | 1,200 hardship traces, 240 a week from Mon 2 Aug 2027 (t-141501 onward), seed 2026; Compass's first reply with planted errors |
| `guideline.py` | text | ops-1.0, ops-1.1 (the anniversary sentence, the stated-work sentence) and the injected guideline |
| `annotators.py` | simulated | readers' habits, slips, fatigue after 45 minutes, Spanish, minutes per reading, hourly rates |
| `prelabel.py` | **REAL** | three samples per trace on weeks 1 and 2 (480 traces) under ops-1.1, Compass's reply hidden |
| `lab.py` | simulated readers | qualification, five weeks of double reading, sessions, adjudication, audit, cost, designs, debt, selection study, automation bias |
| `inject.py` | simulated readers | Daniel x Kevin matrix with and without the anniversary sentence |
| `try_its.py` | mixed | (1) no triple reads; (2) targeted share; (3) **REAL** ops-1.0 pre-labels on 85 traces |
| `app.py` | code | Streamlit annotation screen (`streamlit run app.py`, then `?annotator=marisol&week=1`) |
| `test_app.py` | code | AppTest: the reply stays hidden until the label is saved, then the label locks |

Run: `./run_all.sh` (uses the cache; writes `OUTPUT.txt`). `python3 prelabel.py run` calls the model
for anything uncached and needs `ANTHROPIC_API_KEY`.

Tokens: main pre-label run 1,440 calls, 950,256 input / 55,970 output (about $1.23 at $1 and $5 per
million). Try-it 3: 85 calls (`out/try3_ops10.jsonl`).

`out/prelabel-fixture-draft1.jsonl` is an earlier run of the same script on a draft of the fixture
whose trace text later changed. It was discarded and nothing in the chapter uses it; it is kept so
the spend is on record. After the run, `fixture.py` gained a second seeded stream that turns six in
seven planted wrong offers into correct replies; it changes Compass's reply only, which the model
never sees, so the cache stays valid.

Truss 0.17.0: `truss/annotation.py`, tests in `truss/tests/test_ch14.py`.
