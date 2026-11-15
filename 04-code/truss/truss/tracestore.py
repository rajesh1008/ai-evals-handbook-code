"""Chapter 3: a writable trace store (SQLite now, PostgreSQL later).

One writer appends; evaluators read through `truss.store.open_store`, which is
read-only. The same tables are declared for PostgreSQL in `ddl("postgres")`.
"""
import json
import sqlite3

TABLES = {
    "traces": [("trace_id", "TEXT PRIMARY KEY"), ("conversation_id", "TEXT"),
               ("schema_version", "TEXT"), ("started_at_utc", "TEXT"), ("channel", "TEXT"),
               ("flow", "TEXT"), ("risk_tier", "TEXT"), ("turns", "INTEGER"),
               ("router_version", "TEXT"), ("model_id", "TEXT"), ("temperature", "REAL"),
               ("prompt_version", "TEXT"), ("policy_corpus_version", "TEXT"),
               ("borrower_token", "TEXT"), ("loan_token", "TEXT"), ("state", "TEXT"),
               ("ingested_at_utc", "TEXT")],
    "spans": [("span_id", "TEXT PRIMARY KEY"), ("trace_id", "TEXT REFERENCES traces"),
              ("parent_id", "TEXT"), ("kind", "TEXT"), ("name", "TEXT"), ("seq", "INTEGER"),
              ("attrs", "JSON")],
    "outcomes": [("outcome_id", "TEXT PRIMARY KEY"), ("trace_id", "TEXT"),
                 ("borrower_token", "TEXT"), ("loan_token", "TEXT"), ("kind", "TEXT"),
                 ("occurred_at_utc", "TEXT"), ("value", "TEXT"), ("source", "TEXT")],
    "samples": [("sample_id", "TEXT"), ("trace_id", "TEXT"), ("stratum", "TEXT"),
                ("weight", "REAL")],
}
INDEXES = ["CREATE INDEX IF NOT EXISTS ix_spans_trace ON spans(trace_id)",
           "CREATE INDEX IF NOT EXISTS ix_traces_flow ON traces(flow, started_at_utc)",
           "CREATE INDEX IF NOT EXISTS ix_out_trace ON outcomes(trace_id)",
           "CREATE INDEX IF NOT EXISTS ix_out_borrower ON outcomes(borrower_token, occurred_at_utc)"]


def ddl(dialect="sqlite"):
    stmts = []
    for t, cols in TABLES.items():
        body = []
        for c, ty in cols:
            if dialect == "postgres":
                ty = ty.replace("JSON", "JSONB").replace("REAL", "DOUBLE PRECISION")
                if c.endswith("_utc"):
                    ty = "TIMESTAMPTZ"
            body.append(f"  {c} {ty}")
        stmts.append(f"CREATE TABLE IF NOT EXISTS {t} (\n" + ",\n".join(body) + "\n)")
    return stmts + INDEXES


def create_store(path, wal=True):
    db = sqlite3.connect(path, timeout=5.0 if wal else 0.0)
    if wal:
        db.execute("PRAGMA journal_mode=WAL")
    for s in ddl("sqlite"):
        db.execute(s)
    db.commit()
    return db


def write_trace(db, trace, spans, outcomes=()):
    """Append one trace with its spans. Existing trace IDs are refused, never replaced."""
    cols = [c for c, _ in TABLES["traces"]]
    db.execute(f"INSERT INTO traces ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
               [trace.get(c) for c in cols])
    db.executemany("INSERT INTO spans VALUES (?,?,?,?,?,?,?)",
                   [(s["span_id"], trace["trace_id"], s.get("parent_id"), s["kind"], s["name"],
                     s["seq"], json.dumps(s["attrs"], separators=(",", ":"))) for s in spans])
    db.executemany("INSERT INTO outcomes VALUES (?,?,?,?,?,?,?,?)",
                   [tuple(o[c] for c, _ in TABLES["outcomes"]) for o in outcomes])
