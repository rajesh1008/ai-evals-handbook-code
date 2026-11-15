# Chapter 13 lab: building the gold set with the customer's experts

Everything about the officers is **simulated**. No person labelled these traces: `officers.py`
generates Grace's and Ben's labels, minutes and slips from stated rules, and `lab.py` plays the
adjudicator. The agreement statistics are real computations on those simulated labels. The two model
experiments are **real** calls to Anthropic models, cached in `out/`.

| File | What it does |
|---|---|
| `fixture.py` | 300 hardship traces (262 from harbor-golden v1.1, 38 from 1 to 9 July 2027), seed 2026 |
| `guideline.py` | the hardship gold guideline: draft, revisions 1, 2 and 3, with stable sentence IDs |
| `officers.py` | simulated readers: the two readings that differ, fatigue after 45 minutes, Ben's drift |
| `store.py` | SQLite storage; a reader can query only their own labels; adjudicator sees A and B |
| `app.py` | Streamlit labelling screen (`?annotator=grace`, `?annotator=ben`, `?role=adjudicator`) |
| `lab.py` | pilot, session one, revision 3, adjudication, audit, gold, hours, explanation gold, drift, FM-07 read |
| `try_its.py` | three variations: no audit; single read plus 20%; 90-minute sittings |
| `june_docs.py` | the fresh June document set (160 documents, hd-0201 to hd-0360) from Chapter 11's generator |
| `june_run.py` | REAL: claude-haiku-4-5-20251001 extraction, scored against Victor's rule |
| `probe.py` | REAL: Haiku and Sonnet asked which guideline sentences two officers could read differently |

Run: `./run_all.sh` (cached), or `./run_all.sh run` to call the models for anything uncached.
To open the labelling screen: `GOLD_DB=out/gold.db GOLD_BATCH=session-1 GOLD_GUIDELINE=r2 streamlit run app.py`.
Truss 0.16.0 (`truss/adjudication.py`, tests in `truss/tests/test_ch13.py`).
Tokens: June extraction 137,640 input / 56,385 output; probe 10,248 / 11,850.
