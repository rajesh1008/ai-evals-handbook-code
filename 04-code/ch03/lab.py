"""Chapter 3 Lab: traces worth evaluating, end to end on the v0.5 store."""
import json
import os
import random
import sqlite3
import subprocess
import sys
import time
from collections import Counter

from common import OUT, ORDER, QUOTAS, SHARES, STORE, db, evidence_by_trace, frame, save, truth
from truss import sampling as S
from truss.outcomes import link_fuzzy, matured, score_links
from truss.rates import upper_bound, wilson
from truss.redact import Redactor, evidence_report, residual
from truss.schema import EVIDENCE, gaps, to_otel
from truss.tracestore import ddl

con, T = db(), truth()
F = frame(con)
FLOW = {r["trace_id"]: r["flow"] for r in F}


def spans_of(tid):
    return [{"kind": k, "name": n, "attrs": json.loads(a)} for k, n, a in con.execute(
        "SELECT kind, name, attrs FROM spans WHERE trace_id=? ORDER BY seq", (tid,))]


def trace_row(tid):
    cur = con.execute("SELECT * FROM traces WHERE trace_id=?", (tid,))
    return dict(zip([d[0] for d in cur.description], cur.fetchone()))


# ---------------------------------------------------------------- A. replay
print("== A. Three complaints, three levels of record ==")
LEVELS = {"final answer only": "L0", "pilot trace (Chapter 2)": "L1", "v0.5 trace": "L2"}


def view(tid, level):
    tr, sp = trace_row(tid), spans_of(tid)
    outs = [dict(zip(("kind", "value", "at"), o)) for o in con.execute(
        "SELECT kind, value, occurred_at_utc FROM outcomes WHERE loan_token=? AND kind!='complaint'", (tr["loan_token"],))]
    if level == "L0":
        return {"reply": "[final reply]"}, [], []
    if level == "L1":
        tr = {k: v for k, v in tr.items() if k not in ("prompt_version", "policy_corpus_version", "state")}
        return tr, [s for s in sp if s["kind"] != "retrieve"], []
    return tr, sp, outs


def root_cause(flow, tr, sp, outs):
    if flow == "fee_explanation":
        v = [d for s in sp if s["kind"] == "retrieve" for d in s["attrs"]["doc_versions"]]
        return ("retrieved " + v[0]) if v and "2024" in v[0] else None
    if flow == "hardship":
        h = [s["attrs"]["result"]["prior_deferral_on"] for s in sp
             if s["attrs"].get("tool_name") == "get_account_history"]
        drafted = any(s["attrs"].get("tool_name") == "draft_offer" for s in sp)
        return f"offer drafted despite deferral on {h[0]}" if h and h[0] and drafted else None
    if flow == "lien_release":
        st = tr.get("state")
        rec = [o for o in outs if o["kind"] == "title_recorded"]
        if not (st and rec):
            return None
        from datetime import datetime as _d
        lag = (_d.fromisoformat(rec[0]["at"]) - _d.fromisoformat(tr["started_at_utc"])).days
        return (f"reply promised ten business days; {st} title office recorded after {lag} days"
                if st and rec and lag and lag > 14 else None)
    return None


comp = {c: FLOW[c] for c in T["complaints"]}
incidents = [next(c for c in sorted(comp) if comp[c] == f) for f in
             ("fee_explanation", "hardship", "lien_release")]
replay = {}
for lvl_name, lvl in LEVELS.items():
    found = []
    for tid in incidents:
        tr, sp, outs = view(tid, lvl)
        found.append(root_cause(FLOW[tid], tr, sp, outs))
    replay[lvl_name] = found
    print(f"{lvl_name:<26} root causes identified {sum(bool(x) for x in found)} of 3")
for tid, cause in zip(incidents, replay["v0.5 trace"]):
    print(f"  {tid} {FLOW[tid]:<16} {cause}")
save("replay", {"incidents": incidents, "levels": {k: [bool(x) for x in v] for k, v in replay.items()}})

# ---------------------------------------------------------------- B. contract
print("\n== B. The trace contract ==")
sample_ids = [t for t, _ in S.stratified(F, "flow", QUOTAS)]
g1 = g2 = 0
for tid in sample_ids:
    tr, sp, _ = view(tid, "L1")
    g1 += bool(gaps(tr, sp + [{"kind": "retrieve", "attrs": {}}] * (FLOW[tid] in ("fee_explanation", "hardship"))))
    tr, sp, _ = view(tid, "L2")
    g2 += bool(gaps(tr, sp))
print(f"first-pass sample of 300: traces with contract gaps, pilot schema {g1}, v0.5 schema {g2}")
tr, sp, _ = view(sample_ids[0], "L1")
print("  pilot schema lacks:", sorted({g.split('.')[-1] for g in gaps(tr, sp)}), "+ retrieval spans")
spans_per = con.execute("SELECT COUNT(*)*1.0/(SELECT COUNT(*) FROM traces) FROM spans").fetchone()[0]
kinds = dict(con.execute("SELECT kind, COUNT(*) FROM spans GROUP BY kind"))
print(f"spans per trace {spans_per:.1f}; by kind {kinds}")
hs = [s for s in spans_of(incidents[1]) if s["attrs"].get("tool_name") == "get_account_history"][0]
print("OpenTelemetry view of one tool span:", json.dumps(to_otel(hs)))
letters = con.execute("SELECT COUNT(*) FROM spans WHERE name='execute_tool send_letter' "
                      "AND json_extract(attrs,'$.result.payoff_amount') IS NULL").fetchone()[0]
print(f"payoff traces whose send_letter result shows the amount the borrower received: "
      f"{2587 - letters} of 2587")
save("contract", {"gaps_pilot": g1, "gaps_v05": g2, "spans_per_trace": spans_per, "kinds": kinds})

# ---------------------------------------------------------------- C. redaction
print("\n== C. Redaction before storage ==")
EV = evidence_by_trace(con)
cases = [(e["flow"], e) for e in EV.values()]
rep = evidence_report(Redactor(), cases)
for f in ORDER:
    k, n = rep[f]
    print(f"  {f:<18} evidence kept {k}/{n}")
first = [a for a, in con.execute("SELECT json_extract(attrs,'$.input') FROM spans "
                                 "WHERE kind='chat' AND seq=2")]
tok = Counter(w.split("_")[0] for m in first for w in m.replace(".", " ").split() if "_" in w and w.isupper() is False and w.split("_")[0].isupper())
leaks = [x for m in first for x in residual(m)]
print(f"first borrower messages scanned {len(first)}; tokens inserted {dict(tok)}; "
      f"identity-like strings left {len(leaks)}, e.g. '{leaks[0][:3]} ** ****'")
save("redaction", {"kept": rep, "leaks": len(leaks), "tokens": dict(tok)})

# ---------------------------------------------------------------- D. store
print("\n== D. The trace store ==")
size = os.path.getsize(STORE)
per = size / len(F)
print(f"store {size/1e6:.1f} MB for {len(F)} traces: {per/1e3:.2f} kB per trace")
for share, per_day in (("10%", 570), ("100%", 5700)):
    print(f"  at {share} of traffic ({per_day}/day): {per*per_day*365/1e9:.1f} GB a year, "
          f"{per_day*365*spans_per/1e6:.1f} million spans")
open(OUT / "postgres_ddl.sql", "w").write(";\n\n".join(ddl("postgres")) + ";\n")
t0 = time.perf_counter()
ids = [t for t, in con.execute("SELECT trace_id FROM traces WHERE flow='hardship' ORDER BY trace_id")]
q = (time.perf_counter() - t0) * 1000
print(f"frame query for hardship returned {len(ids)} ids in {q:.0f} ms")
res = {}
for mode in ("rollback", "wal"):
    p = OUT / f"conc_{mode}.db"
    p.unlink(missing_ok=True)
    out = subprocess.run([sys.executable, "concurrency.py", str(p), mode], capture_output=True, text=True)
    res[mode] = out.stdout.strip()
    print(f"  two writers, {mode:<8}: {res[mode]}")
    for ext in ("", "-wal", "-shm"):
        __import__("pathlib").Path(str(p) + ext).unlink(missing_ok=True)
save("store", {"mb": size / 1e6, "kb_per_trace": per / 1e3, "spans_per_trace": spans_per,
               "gb_year_10": per * 570 * 365 / 1e9, "gb_year_100": per * 5700 * 365 / 1e9,
               "concurrency": res})

# ---------------------------------------------------------------- E. sampling
print("\n== E. Four sampling strategies, scored against the planted answer ==")
fail = {t: bool(v) for t, v in T["fail"].items()}
mode = T["mode"]
true_rate = sum(SHARES[f] * sum(fail[r["trace_id"]] for r in F if r["flow"] == f) /
                sum(1 for r in F if r["flow"] == f) for f in ORDER)
pop_rate = sum(fail.values()) / len(fail)
mean_turns = {f: sum(r["turns"] for r in F if r["flow"] == f) / sum(1 for r in F if r["flow"] == f) for f in ORDER}


def risk(r):
    return 1 + 3 * (r["risk_tier"] == "high") + r["turns"] / mean_turns[r["flow"]] + r["handoff"]


def sig(r):
    return (r["flow"], r["prompt_version"], r["channel"])


print(f"planted failure rate: {pop_rate:.4f} ({sum(fail.values())} of {len(fail)} traces)")
STRATS = {
    "uniform": lambda s: S.uniform(F, 300, s),
    "stratified": lambda s: S.stratified(F, "flow", QUOTAS, s),
    "risk-weighted": lambda s: S.risk_weighted(F, 300, risk, s),
}
REPS = 300
sim = {}
for name, draw in STRATS.items():
    est, raw, hard, found, modes = [], [], [], [], []
    for rep_ in range(REPS):
        smp = draw(2026 + rep_)
        est.append(S.hajek(smp, fail))
        raw.append(sum(fail[t] for t, _ in smp) / len(smp))
        hard.append(sum(FLOW[t] == "hardship" for t, _ in smp))
        found.append(100 * sum(fail[t] for t, _ in smp) / len(smp))
        modes.append(len({mode[t] for t, _ in smp if t in mode}))
    m = lambda xs: sum(xs) / len(xs)  # noqa: E731
    rmse = m([(e - pop_rate) ** 2 for e in est]) ** .5
    sim[name] = {"weighted_mean": m(est), "raw_mean": m(raw), "rmse": rmse, "hardship_read": m(hard),
                 "fails_per_100": m(found), "modes_found": m(modes),
                 "hardship_bound_if_clean": upper_bound(0, round(m(hard)))}
    print(f"  {name:<14} weighted est {m(est):.4f} (raw {m(raw):.4f}) rmse {rmse:.4f}; "
          f"hardship read {m(hard):.0f}; failures per 100 read {m(found):.1f}; modes found {m(modes):.1f} of 14")
seeded = S.incident_seeded(F, T["complaints"], sig, 10)
sf = sum(fail[t] for t, _ in seeded)
sim["incident-seeded"] = {"n": len(seeded), "fails": sf, "modes_found": len({mode[t] for t, _ in seeded if t in mode})}
print(f"  incident-seeded: {len(seeded)} traces (14 complaints + look-alikes), {sf} fail = {sf/len(seeded):.1%} "
      f"if wrongly pooled against {pop_rate:.1%} true; modes found {sim['incident-seeded']['modes_found']}")
save("sampling", {"true": pop_rate, "true_weighted": true_rate, "reps": REPS, "sim": sim})

# ---------------------------------------------------------------- F. manifest
print("\n== F. A sample anyone can draw again ==")
ids = [r["trace_id"] for r in F]
smp = S.stratified(F, "flow", QUOTAS)
man = S.manifest("first-pass-2026-10", "stratified", {"key": "flow", "quotas": QUOTAS},
                 "SELECT trace_id, flow FROM traces WHERE started_at_utc < '2026-10-19T07:00:00'",
                 ids, smp, 2026, "0.5.0")
open(OUT / "manifest_first_pass.json", "w").write(S.dumps(man))
again = S.stratified(F, "flow", QUOTAS)
print(f"redraw from manifest: {sum(a == b for a, b in zip(smp, again))} of 300 identical; frame hash {man['frame_sha256']}")
rl = random.Random("late")
late = [{"trace_id": f"t-{rl.getrandbits(32):08x}", "flow": rl.choices(ORDER, [SHARES[f] for f in ORDER])[0]}
        for i in range(37)]   # the new SMS gateway assigns random OpenTelemetry-style ids
F2 = sorted(F + late, key=lambda r: r["trace_id"])
again = {t for t, _ in S.stratified(F2, "flow", QUOTAS)}
changed = len(set(man["trace_ids"]) - again)
print(f"37 late SMS traces added to the frame: naive redraw changes {changed} of 300 ids")
gone = set(random.Random("erase").sample(sorted(ids[:2000]), 4))
F3 = [r for r in F2 if r["trace_id"] not in gone]
again3 = {t for t, _ in S.stratified(F3, "flow", QUOTAS)}
changed3 = len(set(man["trace_ids"]) - again3)
print(f"plus 4 early traces deleted on borrowers' erasure requests: naive redraw changes {changed3} of 300 ids")
try:
    S.verify(man, [r["trace_id"] for r in F3])
except ValueError as e:
    print("verify():", e)
save("manifest", {"identical": 300, "changed_after_late": changed, "changed_after_delete": changed3, "hash": man["frame_sha256"]})

# ---------------------------------------------------------------- G. outcomes
print("\n== G. Linking traces to outcomes ==")
outs = [dict(zip(("outcome_id", "trace_id", "borrower_token", "loan_token", "kind", "occurred_at_utc"), o))
        for o in con.execute("SELECT outcome_id, trace_id, borrower_token, loan_token, kind, occurred_at_utc FROM outcomes")]
print("outcomes by kind:", dict(Counter(o["kind"] for o in outs)))
calls = [o for o in outs if o["kind"] in ("recontact_call", "complaint")]
truth_calls = {o["outcome_id"]: T["links"][o["outcome_id"]] for o in calls if o["outcome_id"] in T["links"]}
link_res = {}
for key in ("borrower_token", "loan_token"):
    found = link_fuzzy(F, calls, 7, key)
    prec, rec = score_links(found, truth_calls)
    link_res[key] = (prec, rec, len(found))
    print(f"  fuzzy join on {key:<15} 7 days: {len(found)} links, precision {prec:.3f}, recall {rec:.3f}")
direct = sum(1 for o in outs if o["trace_id"])
print(f"  direct join (trace id on the event): {direct} officer decisions, precision 1.000 by construction")
fl = link_fuzzy(F, calls, 7, "loan_token")
rc = Counter()
for oid, t in fl.items():
    rc[(FLOW[t], fail[t])] += 1
for f in ORDER:
    nf = sum(1 for r in F if r["flow"] == f and fail[r["trace_id"]])
    npass = sum(1 for r in F if r["flow"] == f) - nf
    print(f"  {f:<18} re-contact within 7 days: failed {rc[(f, True)]/max(1,nf):.1%}, passed {rc[(f, False)]/npass:.1%}")
lien = [r for r in F if r["flow"] == "lien_release"]
rec = {}
for o in con.execute("SELECT outcome_id, loan_token, occurred_at_utc FROM outcomes WHERE kind='title_recorded'"):
    rec[T["links"][o[0]]] = o[2]
from datetime import datetime as D  # noqa: E402
asof = "2026-10-25T00:00:00"
late_by_week = []
for wk in range(6):
    grp = [r for r in lien if f"2026-09-{7+7*wk:02d}" <= r["started_at_utc"][:10] or wk >= 4]
    lo = D(2026, 9, 7 + 7 * wk) if wk < 4 else None
grp_rows = []
from datetime import timedelta  # noqa: E402
for wk in range(6):
    start = D(2026, 9, 7) + timedelta(days=7 * wk)
    g = [r for r in lien if start <= D.fromisoformat(r["started_at_utc"]) < start + timedelta(days=7)]
    seen = [r for r in g if r["trace_id"] in rec]
    slow = [r for r in seen if (D.fromisoformat(rec[r["trace_id"]]) - D.fromisoformat(r["started_at_utc"])).days > 14]
    grp_rows.append((start.date().isoformat(), len(g), len(seen), len(slow)))
    print(f"  lien week of {start.date()}: {len(g)} traces, title recorded for {len(seen)}, "
          f"after 14 days {len(slow)} ({len(slow)/max(1,len(seen)):.0%} of recorded)")
mat = matured(lien, 30, asof)
ms = [r for r in mat if r["trace_id"] in rec and (D.fromisoformat(rec[r["trace_id"]]) - D.fromisoformat(r["started_at_utc"])).days > 14]
allseen = [r for r in lien if r["trace_id"] in rec]
alls = [r for r in allseen if (D.fromisoformat(rec[r["trace_id"]]) - D.fromisoformat(r["started_at_utc"])).days > 14]
print(f"  slow-release rate, all recorded so far: {len(alls)}/{len(allseen)} = {len(alls)/len(allseen):.1%}; "
      f"matured traces only (30+ days old): {len(ms)}/{len(mat)} = {len(ms)/len(mat):.1%}")
save("outcomes", {"links": link_res, "lien_weeks": grp_rows, "slow_all": [len(alls), len(allseen)],
                  "slow_matured": [len(ms), len(mat)]})
