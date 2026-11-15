"""Chapter 3 Try It Yourself: three variations on the Lab."""
import random
from datetime import date, timedelta

from common import ORDER, db, evidence_by_trace, frame, truth
from truss import sampling as S
from truss.outcomes import link_fuzzy, score_links

con, T = db(), truth()
F = frame(con)
fail = {t: bool(v) for t, v in T["fail"].items()}
FLOW = {r["trace_id"]: r["flow"] for r in F}
true = sum(fail.values()) / len(fail)
mt = {f: sum(r["turns"] for r in F if r["flow"] == f) / sum(r["flow"] == f for r in F) for f in ORDER}

print("== Try 1: risk weights and budget ==")
for label, hi, n in (("high tier x3, 300", 3, 300), ("high tier x10, 300", 10, 300), ("high tier x10, 600", 10, 600)):
    risk = lambda r, hi=hi: 1 + hi * (r["risk_tier"] == "high") + r["turns"] / mt[r["flow"]] + r["handoff"]  # noqa: E731
    est, hard = [], []
    for k in range(200):
        smp = S.risk_weighted(F, n, risk, 2026 + k)
        est.append(S.hajek(smp, fail))
        hard.append(sum(FLOW[t] == "hardship" for t, _ in smp))
    rmse = (sum((e - true) ** 2 for e in est) / len(est)) ** .5
    print(f"  {label:<20} hardship read {sum(hard)/len(hard):5.0f}; overall rate rmse {rmse:.4f}")

print("\n== Try 2: delete the date or shift it ==")
EV = evidence_by_trace(con)
start = dict(con.execute("SELECT trace_id, started_at_utc FROM traces WHERE flow='hardship'"))
prior = {t: e["prior_deferral_on"] for t, e in EV.items() if e["flow"] == "hardship" and e.get("prior_deferral_on")}


def within_12(a, b):
    return (b - a).days < 365


ok_del = ok_shift = 0
for t, p in prior.items():
    conv, pd = date.fromisoformat(start[t][:10]), date.fromisoformat(p)
    shift = timedelta(days=random.Random(f"shift|{t}").randrange(-180, 180))
    ok_shift += within_12(pd + shift, conv + shift) == within_12(pd, conv)
print(f"  hardship traces with a prior deferral: {len(prior)}")
print(f"  12-month rule checkable after deleting dates: {ok_del} of {len(prior)}")
print(f"  12-month rule checkable after a consistent per-trace shift: {ok_shift} of {len(prior)}")

print("\n== Try 3: the outcome join window ==")
outs = [dict(zip(("outcome_id", "borrower_token", "kind", "occurred_at_utc"), o)) for o in con.execute(
    "SELECT outcome_id, borrower_token, kind, occurred_at_utc FROM outcomes WHERE kind IN ('recontact_call','complaint')")]
tl = {o["outcome_id"]: T["links"][o["outcome_id"]] for o in outs if o["outcome_id"] in T["links"]}
for days in (3, 7, 14):
    p, r = score_links(link_fuzzy(F, outs, days), tl)
    print(f"  window {days:>2} days: precision {p:.3f}, recall {r:.3f}")
