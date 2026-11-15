# Chapter 3 Lab: Traces Worth Evaluating

Truss v0.5. Harbor Lending and Compass are fictional; every number below is
produced from seed 2026 by `build_store.py` over `../truss/fixtures/compass_pilot.db`.

Run everything: `./run_all.sh` (about 30 seconds; writes `OUTPUT.txt`, then runs the Truss tests).

| Step | File | What it shows |
|---|---|---|
| Fixture | `build_store.py` | Rebuilds the 24,011 pilot traces as a v0.5 store: trace settings, span tree, redacted messages, outcomes; plants a latent pass/fail at the Chapter 2 first-pass rates |
| A | `lab.py` | Three complaints replayed from three levels of record (0, 1 and 3 root causes of 3) |
| B | `lab.py` | The trace contract (`truss.schema.gaps`) and the OpenTelemetry GenAI view of a span |
| C | `lab.py` | Redaction before storage: evidence kept per flow; identity-like strings that slipped through |
| D | `lab.py`, `concurrency.py` | Store size per trace, growth at 100% of traffic, two writers with and without WAL; `out/postgres_ddl.sql` |
| E | `lab.py` | Uniform, stratified, risk-weighted and incident-seeded samples scored against the planted answer (300 repetitions) |
| F | `lab.py` | The sample manifest; why a naive redraw is not reproducible |
| G | `lab.py` | Fuzzy and direct outcome joins; re-contact by verdict; right-censored lien outcomes |
| Injection | `inject.py` | A redaction rule that strips every amount of $1,000 or more, caught by the evidence check |
| Try it | `try_its.py` | Risk weights and budget; deleting vs shifting dates; the join window |

New Truss modules: `schema.py`, `redact.py`, `tracestore.py`, `sampling.py`, `outcomes.py`;
tests in `../truss/tests/test_ch03.py`.

PostgreSQL: `ddl("postgres")` declares the same tables (JSONB, TIMESTAMPTZ). The box has
the PostgreSQL 17 client but no server, so the Lab runs on SQLite; the Postgres DDL is
emitted to `out/postgres_ddl.sql` and checked for dialect by a test, not executed.
