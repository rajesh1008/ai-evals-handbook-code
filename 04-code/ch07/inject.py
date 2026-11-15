"""Chapter 7 failure injection: a frame query that silently drops conversations with a tool error.
The collector marks a conversation status='error' when any tool span errors, even when Compass
recovered. 'Only completed conversations' sounds like hygiene; it removes every tool error."""
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss import notebook as NBK
import february as FEB
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    from lab import CODE, FRAME_SQL, frame, ids, by, risk

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE traces (trace_id TEXT PRIMARY KEY, started_at TEXT, flow TEXT, status TEXT)")
db.executemany("INSERT INTO traces VALUES (?,?,?,?)", [(r["trace_id"], r["started_at"], r["flow"], r["status"]) for r in frame])
BUGGY = ("SELECT trace_id FROM traces WHERE started_at >= '2027-02-01' AND started_at < '2027-02-15' "
         "AND status = 'completed'")
print("\n== injection: the frame query")
for name, sql in (("intended", FRAME_SQL), ("injected", BUGGY)):
    got = [t for (t,) in db.execute(sql)]
    a = NBK.frame_audit(frame, got, declared=("abandoned",))
    print(f"{name:<9} {len(got)} traces; excluded {a['excluded']}; undeclared {a['undeclared'] or 'none'}; audit {'ok' if a['ok'] else 'REFUSE'}")
    if name == "injected":
        bad = set(got)
bf = [r for r in frame if r["trace_id"] in bad]
bdraw = [t for t, _, _ in NBK.pps_quota(bf, "flow", FEB.QUOTAS, risk, seed=2026)]
good = [r for r in frame if r["status"] != "abandoned"]
print("\n== what the injected frame cannot contain")
for name, rows in (("error status", [r for r in good if r["status"] == "error"]), ("completed", [r for r in good if r["status"] == "completed"])):
    k = sum(1 for r in rows if r["cause"])
    print(f"  {name:<12} {len(rows):>5} conversations, planted failures {k:>4} ({k / len(rows):.1%})")
for name, fr_ in (("intended", good), ("injected", bf)):
    print(f"  {name:<9} frame: FM-24 conversations {sum(r['cause'] == 'X_invent' for r in fr_)}, tool errors {sum(r['tool_error'] for r in fr_)}")
bdraw = [t for t, _, _ in NBK.pps_quota(bf, "flow", FEB.QUOTAS, risk, seed=2026)]
sc = NBK.share_check(good, bdraw, "tool_error")
print(f"injected draw (seed 2026): {sum(by[t]['tool_error'] for t in bdraw)} tool errors; shares {len(set(ids) & set(bdraw))} trace with the read fifty; "
      f"tool-error share frame {sc['frame_share']:.1%} sample {sc['sample_share']:.1%} -> {'ok' if sc['ok'] else 'FLAG'}")
sc = NBK.share_check(good, ids, "tool_error")
print(f"intended draw: {sum(by[t]['tool_error'] for t in ids)} tool errors; tool-error share sample {sc['sample_share']:.1%} -> {'ok' if sc['ok'] else 'FLAG'}")
hit = {"intended": 0, "injected": 0}
for seed in range(1, 201):
    for name, fr_ in (("intended", good), ("injected", bf)):
        d = NBK.pps_quota(fr_, "flow", FEB.QUOTAS, risk, seed=seed)
        hit[name] += any(by[t]["cause"] == "X_invent" for t, _, _ in d)
print(f"over 200 seeds, a fifty containing at least one FM-24 conversation: intended {hit['intended'] / 2:.0f}%, injected {hit['injected'] / 2:.0f}%")
