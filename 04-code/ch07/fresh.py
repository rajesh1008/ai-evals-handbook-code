"""Chapter 7 Lab: reproduce the notebook on a fresh fifty with the Truss annotation CLI.
A scripted reader stands in for you: it writes p, or f <open code> :: <note>, from the trace's
planted facts. Replace answers.txt with your own readings to do it for real."""
import contextlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss import notebook as NBK
import february as FEB
with contextlib.redirect_stdout(io.StringIO()):
    import lab as L

OPEN = {"F_waive": "fee defended when tool said waive", "X_wrongloan": "tool called on the other loan",
        "P_perdiem": "per diem left off", "P_goodthru": "good-through date wrong", "X_invent": "answer after tool error",
        "L_early": "release promised early", "L_state": "wrong title state", "L_address": "letter to old address",
        "H_income": "offer before income", "H_refused": "refused over old extension", "H_ignored": "asked for a person, carried on",
        "H_approval": "no approval sentence", "A_date": "balance date wrong", "A_second": "second loan not mentioned",
        "S_month": "wrong month sent", "S_yearend": "year-end asked, monthly sent"}
good = [r for r in L.frame if r["status"] != "abandoned" and r["trace_id"] not in set(L.ids)]
draw = [t for t, _, _ in NBK.pps_quota(good, "flow", FEB.QUOTAS, L.risk, seed=2027)]
traces = [dict(L.by[t], messages=[("borrower", f"({L.by[t]['flow'].replace('_', ' ')} conversation, {L.by[t]['turns']} turns)")]) for t in draw]
out = HERE / "out"
(out / "fresh-sample.json").write_text(json.dumps(traces, default=str))
(out / "answers.txt").write_text("\n".join(
    f"f {OPEN[t['cause']]} :: {OPEN[t['cause']]}" if t["cause"] else "p" for t in traces) + "\n")
nb = out / "fresh-notebook.csv"
nb.unlink(missing_ok=True)
with contextlib.redirect_stdout(io.StringIO()) as shown:
    NBK.main(["code", str(out / "fresh-sample.json"), str(nb), "--annotator", "you", "--script", str(out / "answers.txt")])
print("\n== Lab: a fresh fifty, seed 2027, read fifty excluded")
print("CLI screen, first trace:\n" + "\n".join(shown.getvalue().splitlines()[:2]))
print(shown.getvalue().splitlines()[-1])
entries = NBK.read(nb)
for e in entries:
    e.cluster = L.CODE[[k for k, v in OPEN.items() if v == e.open_code][0]] if e.verdict == "fail" else ""
NBK.write(entries, nb)
NBK.report(entries)
found = Counter(e.cluster for e in entries if e.verdict == "fail")
print("v0.3 codes found:", dict(sorted(found.items())), "; new since v0.3:", [c for c in found if c not in L.t03.modes] or "none")
print(f"tool errors in the fresh fifty: {sum(L.by[t]['tool_error'] for t in draw)}")
