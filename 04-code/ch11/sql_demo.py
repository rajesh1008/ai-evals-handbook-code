import json
from sql_lab import Q, OUT, run, same
gen = {s["n"]: s["sql"] for s in json.load(open(OUT / "sql-scores.json"))}
question, gold = Q[13]
print(question)
for db in ("dev.db", "probe.db"):
    g, m = run(OUT / db, gold), run(OUT / db, gen[14])
    print(f"{db:9} gold {g}  generated {m}  match {same(g, m)}")
