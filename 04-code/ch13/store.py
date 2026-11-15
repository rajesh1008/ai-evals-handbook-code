"""SQLite storage for blind double labelling. A reader can fetch only their own labels; the
adjudicator sees disagreements with readers anonymised as A and B in a per-trace random order."""
import random
import sqlite3

SCHEMA = """
create table if not exists traces(trace_id text primary key, batch text, body text);
create table if not exists labels(trace_id text, annotator text, label text, guideline text, minutes real,
  sitting text, minute_in_sitting real, labelled_on text, reason text, policy_question int,
  primary key(trace_id, annotator, guideline, labelled_on));
"""


def connect(path):
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    return db


def load(db, traces, batch, render):
    db.executemany("insert or replace into traces values(?,?,?)", [(t["trace_id"], batch, render(t)) for t in traces])
    db.commit()


def next_trace(db, annotator, batch, guideline):
    row = db.execute("""select trace_id, body from traces where batch=? and trace_id not in
        (select trace_id from labels where annotator=? and guideline=?) order by rowid limit 1""",
                     (batch, annotator, guideline)).fetchone()
    return row


def save(db, lab):
    db.execute("insert or replace into labels values(?,?,?,?,?,?,?,?,?,?)",
               (lab.trace_id, lab.annotator, lab.label, lab.guideline, lab.minutes, lab.sitting, lab.minute_in_sitting,
                lab.labelled_on, lab.reason, int(lab.policy_question)))
    db.commit()


def mine(db, annotator):
    """The only label query a reader's screen can make."""
    return db.execute("select trace_id, label from labels where annotator=?", (annotator,)).fetchall()


def disagreements(db, guideline, a="grace", b="ben"):
    rows = db.execute("""select x.trace_id, x.label, x.reason, y.label, y.reason, t.body from labels x
        join labels y on x.trace_id=y.trace_id and y.annotator=? and y.guideline=x.guideline
        join traces t on t.trace_id=x.trace_id where x.annotator=? and x.guideline=? and x.label<>y.label""",
                      (b, a, guideline)).fetchall()
    out = []
    for tid, la, ra, lb, rb, body in rows:
        pair = [(la, ra), (lb, rb)]
        random.Random(tid).shuffle(pair)  # the adjudicator cannot tell who is A
        out.append({"trace_id": tid, "A": pair[0], "B": pair[1], "body": body})
    return out
