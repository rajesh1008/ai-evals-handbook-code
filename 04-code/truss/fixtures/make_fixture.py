"""Build the Chapter 2 fixture: six weeks of Compass pilot traces (synthetic).

Harbor Lending and Compass are fictional. Every number here is generated
from a fixed seed so the book's printed output reproduces exactly.
"""
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SEED = 2026
DB = Path(__file__).resolve().parent / "compass_pilot.db"
START = datetime(2026, 9, 7, 8, 0)          # pilot launch, Monday 7 September 2026
DAYS = 42                                    # six weeks
DAILY_MEAN = 560                             # 10% of chat and SMS traffic

# flow: (share of traffic, risk tier, mean turns)
FLOWS = {
    "account_question":  (0.41, "low",    4),
    "fee_explanation":   (0.22, "medium", 7),
    "statement_request": (0.14, "low",    4),
    "payoff_letter":     (0.11, "medium", 6),
    "lien_release":      (0.06, "medium", 8),
    "hardship":          (0.06, "high",   14),
}


def build(path=DB, seed=SEED):
    rng = random.Random(seed)
    if path.exists():
        path.unlink()
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE traces (
        trace_id TEXT PRIMARY KEY, started_at TEXT, channel TEXT,
        flow TEXT, risk_tier TEXT, turns INTEGER)""")
    names, weights = list(FLOWS), [v[0] for v in FLOWS.values()]
    n = 0
    for day in range(DAYS):
        for _ in range(int(rng.gauss(DAILY_MEAN, 40))):
            flow = rng.choices(names, weights)[0]
            _, tier, mean_turns = FLOWS[flow]
            n += 1
            ts = START + timedelta(days=day, seconds=rng.randrange(14 * 3600))
            turns = max(2, int(rng.gauss(mean_turns, mean_turns / 3)))
            db.execute("INSERT INTO traces VALUES (?,?,?,?,?,?)",
                       (f"t-{n:06d}", ts.isoformat(), rng.choice(["sms", "chat"]),
                        flow, tier, turns))
    # Ryan's spreadsheet: the first 40 conversations the review screen showed,
    # which sorts the first two days by length, shortest first.
    db.execute("CREATE TABLE ryan_sheet (trace_id TEXT PRIMARY KEY, verdict TEXT)")
    db.execute("""INSERT INTO ryan_sheet
        SELECT trace_id, 'fine' FROM traces
        WHERE started_at < ? ORDER BY turns, trace_id LIMIT 40""",
               ((START + timedelta(days=2)).isoformat(),))
    db.commit()
    return db


if __name__ == "__main__":
    db = build()
    print(db.execute("SELECT COUNT(*) FROM traces").fetchone()[0], "traces written to", DB.name)
