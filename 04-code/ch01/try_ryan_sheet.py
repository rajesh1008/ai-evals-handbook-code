"""Try it yourself 3: replay Ryan's 40 hand-picked conversations instead."""
from collections import Counter

from replay import flipped, open_store, pass_hat_k, replay

db = open_store()
cols = [r[1] for r in db.execute("PRAGMA table_info(ryan_sheet)")]
print("ryan_sheet columns:", cols)
convs = db.execute("SELECT r.trace_id, t.flow FROM ryan_sheet r "
                   "JOIN traces t USING (trace_id) ORDER BY r.trace_id").fetchall()
print("flows:", dict(Counter(f for _, f in convs)))
res = replay(convs, runs=3, temperature=0.7)
print(f"flipped {len(flipped(res))} of {len(res)}, pass^3 = {pass_hat_k(res, 3):.0%}")
