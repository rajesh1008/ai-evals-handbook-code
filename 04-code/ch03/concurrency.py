"""Two processes append to one SQLite file at once; count the writes refused."""
import multiprocessing as mp
import sqlite3
import sys


def writer(path, mode, n, start, q):
    db = sqlite3.connect(path, timeout=0.0 if mode == "rollback" else 5.0, isolation_level=None)
    refused = 0
    for i in range(n):
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO spans VALUES (?, ?)", (f"s{start + i}", "x" * 400))
            db.execute("COMMIT")
        except sqlite3.OperationalError:
            refused += 1
            try:
                db.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
    q.put(refused)


if __name__ == "__main__":
    path, mode = sys.argv[1], sys.argv[2]
    db = sqlite3.connect(path)
    if mode == "wal":
        db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE spans (span_id TEXT PRIMARY KEY, attrs TEXT)")
    db.commit(); db.close()
    q = mp.Queue()
    ps = [mp.Process(target=writer, args=(path, mode, 2000, k * 10_000, q)) for k in range(2)]
    [p.start() for p in ps]; [p.join() for p in ps]
    refused = q.get() + q.get()
    print(f"{4000 - refused} of 4000 span writes stored, {refused} refused with 'database is locked'")
