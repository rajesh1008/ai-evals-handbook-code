"""Chapter 9 lab: eight code checks for Compass.
A the April fixture and one trace; B format and schema; C policy rules (window, boundary, approval
sentence, callback); D arithmetic (fees, payoff); E citations and number provenance; F composition
(order, cannot-tell, overlap, run time); G the fee replay set and the gate (80 new cases, three
candidates); H census rates, the MC-01 offer census and the April fee draw; I validation (precision
from every flag, recall from a read sample, mutation scores); J hours and dollars; K check coverage.
Run: python3 lab.py   (writes out/lab.json)"""
import copy
import json
import random
import re
import statistics as st
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
sys.path.insert(0, str(HERE.parents[0] / "ch08"))
import truss  # noqa: E402
from truss import checks as K  # noqa: E402
from truss import notebook as NBK  # noqa: E402
from truss import taxonomy as T  # noqa: E402
from truss.rates import upper_bound, wilson  # noqa: E402
from truss.sampling import stratified  # noqa: E402
import february as FEB  # noqa: E402
import march as MAR  # noqa: E402
import april as A  # noqa: E402
import compass_checks as CC  # noqa: E402
from scipy.stats import binom  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
R = {"truss": truss.__version__}
FAILS = lambda res, v: {t for t, r in res.items() if r[v].outcome == K.FAIL}  # noqa: E731


def head(s):
    print(f"\n== {s}")


def pct(k, n):
    if n == 0:
        return f"{k} in 0"
    lo, hi = wilson(k, n)
    return f"{k} in {n} ({k / n:.1%}, Wilson {lo:.1%} to {hi:.1%})"


# ---- A. fixture
head("A. The April fixture (Thu 1 to Wed 14 April 2027), release rc-0326-2")
rows = A.build()
t0 = time.perf_counter()
apr = [A.render(r) for r in rows]
render_s = time.perf_counter() - t0
by = {t["trace_id"]: t for t in apr}
rowby = {r["trace_id"]: r for r in rows}
flows = Counter(t["flow"] for t in apr)
print(f"Truss {truss.__version__}; {len(apr):,} conversations, {apr[0]['trace_id']} to {apr[-1]['trace_id']}; "
      f"seed {A.SEED}; flows {dict(flows)}")
print(f"spans {sum(len(t['spans']) for t in apr):,}; tool spans in error {sum(s['status'] == 'error' for t in apr for s in t['spans'])}; "
      f"Spanish hardship conversations {sum(t['lang'] == 'es' for t in apr)}; two-loan accounts "
      f"{sum(len(t['account']['loans']) == 2 for t in apr)}")
print("planted truth (what no team sees):", dict(Counter(x for t in apr for x in t["truth"]).most_common()))
ex = next(t for t in apr if t["flow"] == "payoff_letter" and "FM-19" in t["truth"] and len(t["spans"]) == 2)
print("one trace:", json.dumps({k: ex[k] for k in ("trace_id", "started_at", "flow", "message", "reply")}))
print("  payoff span:", json.dumps(ex["spans"][1]))
R["fixture"] = {"n": len(apr), "first": apr[0]["trace_id"], "last": apr[-1]["trace_id"], "flows": dict(flows),
                "truth": dict(Counter(x for t in apr for x in t["truth"])), "example": ex["trace_id"]}

S = CC.suite()
res, secs = S.run_all(apr)
R["runtime"] = {"traces": len(apr), "seconds": secs, "per_1000": secs / len(apr) * 1000}

# ---- B. format and schema
head("B. C-01 tool_returns: every tool call's arguments and return, and the reply after a failure")
calls = Counter(s["tool"] for t in apr for s in t["spans"])
invalid = Counter(s["tool"] for t in apr for s in t["spans"] if not CC.valid_return(s))
c01 = FAILS(res, "C-01")
fig_after = Counter()
for t in apr:
    bad = [s["tool"] for s in t["spans"] if not CC.valid_return(s)]
    if bad:
        fig_after["flagged" if t["trace_id"] in c01 else "passed"] += 1
print(f"{'tool':<28}{'calls':>7}{'invalid':>9}{'replies flagged':>17}")
tool_rows = []
for tool, n in calls.most_common():
    fl = sum(1 for t in c01 if any(s["tool"] == tool and not CC.valid_return(s) for s in by[t]["spans"]))
    tool_rows.append((tool, n, invalid[tool], fl))
    print(f"{tool:<28}{n:>7}{invalid[tool]:>9}{fl:>17}")
print(f"conversations with an invalid return {sum(fig_after.values())}: reply states a figure or done action "
      f"{fig_after['flagged']} (FM-24), states none {fig_after['passed']}; truth FM-24 {sum('FM-24' in t['truth'] for t in apr)}")
print("by flow:", dict(Counter(by[t]["flow"] for t in c01)))
x = by[sorted(c01)[0]]
print(f"example {x['trace_id']}: {res[x['trace_id']]['C-01'].evidence} | reply: {x['reply'][:120]}")
# schema-valid but wrong: a per diem of zero passes C-01, C-07 catches it
pay_ok = [t for t in apr if t["flow"] == "payoff_letter" and res[t["trace_id"]]["C-07"].outcome == K.PASS]


def zero_pd(t):
    m = copy.deepcopy(t)
    m["spans"][1]["result"]["per_diem"] = 0.0
    return m


z = [zero_pd(t) for t in pay_ok[:100]]
zr = [S.run(m) for m in z]
print(f"schema-valid nonsense: per diem set to 0.00 in 100 correct quotes -> C-01 passes "
      f"{sum(r['C-01'].outcome == K.PASS for r in zr)}, C-07 fails {sum(r['C-07'].outcome == K.FAIL for r in zr)}")
R["schema"] = {"tools": tool_rows, "flagged": fig_after["flagged"], "quiet": fig_after["passed"],
               "zero_pd": [sum(r['C-01'].outcome == K.PASS for r in zr), sum(r['C-07'].outcome == K.FAIL for r in zr)]}

# ---- C. policy rules
head("C1. C-03 deferral_window on April hardship conversations")
hard = [t for t in apr if t["flow"] == "hardship"]
c03 = Counter((res[t["trace_id"]]["C-03"].data.get("kind", "-"), res[t["trace_id"]]["C-03"].outcome) for t in hard)
print(f"hardship {len(hard)}; outcomes by kind {dict(c03)}")
for t in sorted(FAILS(res, "C-03"))[:3]:
    print(f"  {t} {res[t]['C-03'].evidence}")
ref_fail = [t for t in FAILS(res, "C-03") if res[t]["C-03"].data.get("kind") == "refusal"]
off_fail = [t for t in FAILS(res, "C-03") if res[t]["C-03"].data.get("kind") == "offer"]
print(f"refusals failing (FM-20) {len(ref_fail)}; offers failing (FM-04) {len(off_fail)} {off_fail}")
R["window"] = {"outcomes": {f"{a}/{b}": n for (a, b), n in c03.items()}, "refusal_fail": len(ref_fail),
               "offer_fail": off_fail}

head("C2. Boundary cases for the twelve-month window: the check (calendar months, Grace's ruling) vs the eligibility "
     "tool (days <= 365)")
cases = [("relief ended 364 days before", date(2026, 4, 6), date(2027, 4, 5)),
         ("ended 365 days before (same calendar date)", date(2026, 4, 5), date(2027, 4, 5)),
         ("ended 366 days before", date(2026, 4, 4), date(2027, 4, 5)),
         ("same calendar date across 29 Feb 2028 (366 days)", date(2027, 3, 1), date(2028, 3, 1)),
         ("ended 29 Feb 2028, asked 28 Feb 2029", date(2028, 2, 29), date(2029, 2, 28)),
         ("ended 31 Mar 2027, asked 30 Mar 2028", date(2027, 3, 31), date(2028, 3, 30)),
         ("ended on the day of the conversation", date(2027, 4, 5), date(2027, 4, 5)),
         ("ends after the conversation (still running)", date(2027, 5, 1), date(2027, 4, 5))]
brow = []
for label, end, asof in cases:
    chk = K.within_months(end, asof, 12)
    tool = 0 <= (asof - end).days <= 365
    brow.append({"case": label, "end": end.isoformat(), "asked": asof.isoformat(), "days": (asof - end).days,
                 "check_inside": chk, "tool_inside": tool, "agree": chk == tool})
    print(f"  {label:<52} {(asof - end).days:>4} days  check {'inside ' if chk else 'outside'}  tool "
          f"{'inside ' if tool else 'outside'}  {'agree' if chk == tool else 'DISAGREE'}")
R["boundary"] = brow
# how often the disagreement would bite: conversations in Mar 2028 to Feb 2029 with relief ending a year earlier
print("  (the fixture's April 2027 dates never cross 29 February, so check and tool agree on every April trace)")

head("C3. C-04 approval_sentence: v1.0 (one exact sentence) vs v2.0 (Victor's allow-list) on April offers")
S1 = CC.suite(approval="1.0")
res1, _ = S1.run_all(hard)
offers = [t for t in hard if CC.spans(t, "draft_offer")]
tags = Counter(t["meta"]["approval"] for t in offers)
f1 = Counter(t["meta"]["approval"] for t in offers if res1[t["trace_id"]]["C-04"].outcome == K.FAIL)
f2 = Counter(t["meta"]["approval"] for t in offers if res[t["trace_id"]]["C-04"].outcome == K.FAIL)
print(f"offers drafted {len(offers)}; wording on the offer: {dict(tags)}")
print(f"v1.0 flags {sum(f1.values())}: {dict(f1)}")
print(f"v2.0 flags {sum(f2.values())}: {dict(f2)}")
true04 = {t["trace_id"] for t in offers if "FM-03" in t["truth"]}
miss_only = {t["trace_id"] for t in offers if t["meta"]["approval"] == "missing"}
fl1 = {t["trace_id"] for t in offers if res1[t["trace_id"]]["C-04"].outcome == K.FAIL}
print(f"v1.0 precision against sentence missing (before Victor's ruling): {len(fl1 & miss_only)}/{len(fl1)}; "
      f"after the ruling (para-C is a failure): {len(fl1 & true04)}/{len(fl1)}")
print(f"v2.0 precision {len(FAILS(res, 'C-04') & true04)}/{len(FAILS(res, 'C-04'))}")
R["approval"] = {"offers": len(offers), "tags": dict(tags), "v1": dict(f1), "v2": dict(f2),
                 "v1_prec_before": [len(fl1 & miss_only), len(fl1)], "v1_prec_after": [len(fl1 & true04), len(fl1)]}

head("C4. C-05 callback_hours")
hand = [t for t in apr if CC.spans(t, "request_handoff")]
closed = [t for t in hand if not CC.spans(t, "request_handoff")[0]["result"]["queue_open"]]
print(f"hand-offs {len(hand)}; queue closed {len(closed)} (Spanish {sum(t['lang'] == 'es' for t in closed)}); "
      f"C-05 fails {len(FAILS(res, 'C-05'))}: {sorted(FAILS(res, 'C-05'))}")
for t in sorted(FAILS(res, "C-05"))[:2]:
    print(f"  {t} {by[t]['started_at']} {res[t]['C-05'].evidence}")
R["callback"] = {"handoffs": len(hand), "closed": len(closed), "fails": sorted(FAILS(res, "C-05"))}

head("C5. C-02 named_loan")
named_d = [t for t in apr if CC.DIGITS.search(t["message"])]
c02 = FAILS(res, "C-02")
nick = [t for t in apr if "FM-22" in t["truth"] and res[t["trace_id"]]["C-02"].outcome != K.FAIL]
print(f"conversations naming a loan by digits {len(named_d)}; C-02 fails {len(c02)}; FM-22 by nickname missed {len(nick)}")
print("C-02 fails by flow:", dict(Counter(by[t]["flow"] for t in c02)))
R["named"] = {"digits": len(named_d), "fails": len(c02), "nick_missed": len(nick)}

# ---- D. arithmetic
head("D1. C-07 payoff_arithmetic: the quote recomputed from the loan record, and the reply against the quote")
pay = [t for t in apr if t["flow"] == "payoff_letter"]
oc7 = Counter(res[t["trace_id"]]["C-07"].outcome for t in pay)
side = Counter(res[t["trace_id"]]["C-07"].data.get("side") for t in pay if res[t["trace_id"]]["C-07"].outcome == K.FAIL)
print(f"payoff conversations {len(pay)}; C-07 {dict(oc7)}; failures by side {dict(side)}")
tool_f = [t for t in pay if res[t["trace_id"]]["C-07"].data.get("side") == "tool"]
short = [-res[t["trace_id"]]["C-07"].data["payoff_diff"] for t in tool_f]
wd = Counter(date.fromisoformat(CC.spans(by[t["trace_id"]], "get_payoff_quote")[0]["result"]["good_through"]).strftime("%a")
             for t in tool_f)
print(f"tool-side: {len(tool_f)} quotes short; shortfall mean ${st.mean(short):.2f}, max ${max(short):.2f}, total "
      f"${sum(short):,.2f}; good-through weekday {dict(wd)}")
print(f"  example {tool_f[0]['trace_id']}: {res[tool_f[0]['trace_id']]['C-07'].evidence}")
fac = Counter()
for t in pay:
    r = res[t["trace_id"]]["C-07"]
    if r.outcome == K.FAIL and r.data.get("side") == "reply":
        fac[re.sub(r"[\d$.,-]+", "#", r.evidence)[:40]] += 1
print("reply-side facets:", dict(fac))
quotes_ok = sum(1 for t in pay if CC.spans(t, "get_payoff_quote") and CC.valid_return(CC.spans(t, "get_payoff_quote")[0]))
print(f"payoff quotes returned {quotes_ok}; Sunday share {len(tool_f) / quotes_ok:.1%}")
R["payoff"] = {"n": len(pay), "outcomes": dict(oc7), "side": dict(side), "tool_short": len(tool_f),
               "short_mean": st.mean(short), "short_max": max(short), "short_total": sum(short), "facets": dict(fac),
               "quotes": quotes_ok, "diffs_tool": short,
               "diffs_reply_pd": [res[t["trace_id"]]["C-07"].data.get("per_diem_diff", 0) for t in pay]}

head("D2. C-06 fee_figures on April fee conversations; v1.0 as first written vs v1.1")
fee = [t for t in apr if t["flow"] == "fee_explanation"]
Sv10 = CC.suite(fee="1.0")
r10, _ = Sv10.run_all(fee)
for nm, rr in (("v1.0", r10), ("v1.1", res)):
    fl = {t["trace_id"] for t in fee if rr[t["trace_id"]]["C-06"].outcome == K.FAIL}
    tru = {t["trace_id"] for t in fee if set(t["truth"]) & CC.TARGET["C-06"]}
    print(f"{nm}: outcomes {dict(Counter(rr[t['trace_id']]['C-06'].outcome for t in fee))}; precision "
          f"{len(fl & tru)}/{len(fl)}; FM-06 in frame {len(tru)}, caught {len(fl & tru)}")
fl10 = [t["trace_id"] for t in fee if r10[t["trace_id"]]["C-06"].outcome == K.FAIL and not set(t["truth"]) & CC.TARGET["C-06"]]
print(f"  v1.0 false flag example {fl10[0]}: {r10[fl10[0]]['C-06'].evidence} | {by[fl10[0]]['reply'][:110]}")
phr = Counter(t["meta"]["fee_phrase"] for t in fee if "FM-06" in t["truth"])
print(f"FM-06 phrasings in April: {dict(phr)}")
R["fee"] = {"n": len(fee), "v10_false": len(fl10), "phrases": dict(phr),
            "v11_caught": len(FAILS({t['trace_id']: res[t['trace_id']] for t in fee}, 'C-06'))}

# ---- E. citations
head("E. C-08 citations and number provenance")
c08 = FAILS(res, "C-08")
cited = [t for t in apr if CC.CITE.search(t["reply"])]
kinds = Counter()
for t in c08:
    e = res[t]["C-08"].evidence
    kinds["superseded document"] += "superseded" in e
    kinds["section off topic"] += "is about" in e
    kinds["number with no source"] += "no source" in e
print(f"replies with a citation {len(cited)}; C-08 fails {len(c08)}: {dict(kinds)}")
print("C-08 fails by planted truth:", dict(Counter(tuple(by[t]["truth"]) or ("none",) for t in c08).most_common(8)))
stale = [t for t in apr if "cite:stale" in t["truth"]]
print(f"hardship replies citing HP-2026-09 after 1 April: {len(stale)} of {sum(1 for t in cited if t['flow'] == 'hardship')} "
      f"hardship citations")
inv = [t for t in apr if "FM-24" in t["truth"]]
inv_miss = [t["trace_id"] for t in inv if t["trace_id"] not in c08]
print(f"FM-24 replies {len(inv)}; provenance catches {len(inv) - len(inv_miss)}; misses {len(inv_miss)} (every number "
      f"is in the cited fee schedule) e.g. {inv_miss[:2]}")
fm07 = [t for t in apr if "FM-07" in t["truth"]]
print(f"FM-07 (wrong balance date, a layer-two mode) caught as a side effect: {sum(t['trace_id'] in c08 for t in fm07)} of {len(fm07)}")
Snv = CC.suite(use_verified=False)
rnv, _ = Snv.run_all(pay)
der = [t for t in pay if t["meta"].get("derived")]
print(f"payoff replies with a worked 'if you pay on' figure {len(der)}: C-08 without C-07's verified numbers fails "
      f"{sum(rnv[t['trace_id']]['C-08'].outcome == K.FAIL for t in der)}; with them {sum(t['trace_id'] in c08 for t in der)}")
R["cite"] = {"cited": len(cited), "fails": len(c08), "kinds": dict(kinds), "stale": len(stale),
             "fm24": [len(inv), len(inv) - len(inv_miss)], "fm07": [len(fm07), sum(t['trace_id'] in c08 for t in fm07)],
             "derived": [len(der), sum(rnv[t['trace_id']]['C-08'].outcome == K.FAIL for t in der),
                         sum(t['trace_id'] in c08 for t in der)]}

# ---- F. composition
head("F. Composition: order, cannot-tell, trace verdicts, overlap, run time")
print("run order:", " -> ".join(f"{v} {S.by_id[v].name}" for v in S.order), "; C-06 and C-07 need C-01 and C-02")
tal = {v: K.tally(res, v) for v in S.order}
for v in S.order:
    print(f"  {v} {S.by_id[v].name:<18} {tal[v]}")
ver = Counter(K.verdict(r) for r in res.values())
up = Counter(r[v].evidence for r in res.values() for v in ("C-06", "C-07") if r[v].outcome == K.CANNOT)
print(f"trace verdicts {dict(ver)}; cannot-tell share {ver[K.CANNOT] / len(apr):.2%}; cannot-tell reasons {dict(up)}")
ids = list(S.order)
ov = K.overlap(res, ids)
print("co-flag matrix (diagonal = flagged):")
print("      " + " ".join(f"{v:>5}" for v in ids))
for a in ids:
    print(f"{a:>5} " + " ".join(f"{ov[a][b]:>5}" for b in ids))
anyf = {t for t, r in res.items() if K.verdict(r) == K.FAIL}
print(f"traces failing at least one check {len(anyf)} ({len(anyf) / len(apr):.1%}); failing two or more "
      f"{sum(1 for r in res.values() if sum(x.outcome == K.FAIL for x in r.values()) >= 2)}")
print(f"run time: {len(apr):,} traces in {secs:.2f} s ({secs / len(apr) * 1000:.2f} s per 1,000); rendering took "
      f"{render_s:.2f} s")
R["compose"] = {"tally": tal, "verdicts": dict(ver), "overlap": ov, "any_fail": len(anyf), "order": ids}

# ---- G. replay set and gate
head("G1. Fee replay set (fee-replay-2027-03): which checks catch the 18 wrong-fee cases in production")
rep = A.replay_rows()
rel_res = {}
for rel in ("production", "rc-0322-1", "rc-0326-2"):
    trs = [A.render(r, rel) for r in rep]
    rr, _ = S.run_all(trs)
    rel_res[rel] = (trs, rr)
    wrong = [t for t in trs if t["meta"].get("wrong_fee")]
    caught = [t for t in wrong if K.verdict(rr[t["trace_id"]]) == K.FAIL]
    by_mode = Counter((tuple(t["truth"]), tuple(v for v in ids if rr[t["trace_id"]][v].outcome == K.FAIL)) for t in wrong)
    fp = [t["trace_id"] for t in trs if not t["meta"].get("wrong_fee") and K.verdict(rr[t["trace_id"]]) == K.FAIL]
    print(f"{rel}: wrong fee {len(wrong)} of {len(trs)}; code checks alone fail {len(caught)} "
          f"({len(caught) / max(1, len(wrong)):.0%}); other cases failing a check {len(fp)} {fp[:5]}")
    for (tr_, ch), n in sorted(by_mode.items(), key=lambda z: -z[1]):
        print(f"    truth {','.join(tr_):<22} caught by {','.join(ch) or 'nothing':<16} {n}")
    if rel == "production":
        R["replay_prod"] = {"wrong": len(wrong), "caught": len(caught),
                            "by": [[list(a), list(b), n] for (a, b), n in by_mode.items()]}
    if rel == "rc-0322-1":
        rec = [t for t in trs if "recite" in t["truth"]]
        print(f"    rc-0322-1 recited fees {len(rec)}: C-08 fails {sum(rr[t['trace_id']]['C-08'].outcome == K.FAIL for t in rec)}, "
              f"C-06 fails {sum(rr[t['trace_id']]['C-06'].outcome == K.FAIL for t in rec)}; ids {[t['trace_id'] for t in rec]}")
        R["recite"] = {"n": len(rec), "c08": sum(rr[t['trace_id']]['C-08'].outcome == K.FAIL for t in rec),
                       "c06": sum(rr[t['trace_id']]['C-06'].outcome == K.FAIL for t in rec)}
prod_trs, prod_rr = rel_res["production"]
missed = [t for t in prod_trs if t["meta"].get("wrong_fee") and K.verdict(prod_rr[t["trace_id"]]) != K.FAIL]
print("  missed in production:", [(t["trace_id"], t["meta"]["fee_phrase"]) for t in missed])
Sneg = CC.suite(negation=True)
rneg, _ = Sneg.run_all(prod_trs)
w = [t for t in prod_trs if t["meta"].get("wrong_fee")]
print(f"  with the negation rule (C-06 +negation): caught {sum(K.verdict(rneg[t['trace_id']]) == K.FAIL for t in w)} of {len(w)}; "
      f"other cases failing {sum(1 for t in prod_trs if not t['meta'].get('wrong_fee') and K.verdict(rneg[t['trace_id']]) == K.FAIL)}")

head("G2. The gate: 300 frozen + 270 fee replay + 80 new permanent cases (40 tool failure, 40 two-loan by digits)")
g = random.Random(2026)
terr_pool = sorted([r["trace_id"] for r in rows if r["tool_error"] and r["flow"] in
                    ("fee_explanation", "payoff_letter", "account_question", "hardship")])
dig_pool = sorted([r["trace_id"] for r in rows if r["named_by_digits"] and not r["tool_error"]])
new_tf = g.sample(terr_pool, 40)
new_dg = g.sample(dig_pool, 40)
print(f"pools: tool-error conversations {len(terr_pool)}, two-loan named by digits {len(dig_pool)}; drawn 40 + 40, seed 2026")
print(f"  tool-failure cases by flow {dict(Counter(rowby[t]['flow'] for t in new_tf))}; two-loan cases by flow "
      f"{dict(Counter(rowby[t]['flow'] for t in new_dg))}")
frozen = A.frozen_rows()


def gate_set(rel):
    out = [A.render(r, rel, gate=True) for r in frozen]
    out += [A.render(r, rel) for r in rep]
    for t in new_tf:
        r = dict(rowby[t], gate_tool_error=True)
        out.append(A.render(r, rel, gate=True))
    for t in new_dg:
        out.append(A.render(dict(rowby[t]), rel, gate=True))
    return out


gate = {}
for rel in ("rc-0326-2", "rc-0412-1", "rc-0414-2"):
    gs = gate_set(rel)
    gr, gsec = S.run_all(gs)
    gate[rel] = (gs, gr, gsec)
base_gs, base_gr, _ = gate["rc-0326-2"]
print(f"gate cases {len(base_gs)}; code-check run {gate['rc-0326-2'][2]:.2f} s")
spanish_offers = [t["trace_id"] for t in base_gs if t["lang"] == "es" and CC.spans(t, "draft_offer")]
print(f"Spanish offers in the gate set {len(spanish_offers)}")
grow = {}
for rel in ("rc-0412-1", "rc-0414-2"):
    gs, gr, _ = gate[rel]
    print(f"\n{rel} vs production (rc-0326-2):")
    hold = False
    grow[rel] = {}
    for v in ids:
        b = FAILS(base_gr, v)
        a = FAILS(gr, v)
        newly, fixed = sorted(a - b), sorted(b - a)
        hold |= bool(newly)
        grow[rel][v] = {"before": len(b), "after": len(a), "newly": newly, "fixed": len(fixed)}
        print(f"  {v} {S.by_id[v].name:<18} {len(b):>4} -> {len(a):>4}   newly failing {len(newly):>3} {newly[:4]}  fixed {len(fixed)}")
    print(f"  decision: {'HOLD' if hold else 'SHIP'}")
    grow[rel]["decision"] = "hold" if hold else "ship"
nt = {t["trace_id"]: t for t in base_gs}
newcases = new_tf + new_dg
for rel in ("rc-0326-2", "rc-0412-1"):
    gs, gr, _ = gate[rel]
    m = {t["trace_id"]: t for t in gs}
    f22 = sum(gr[t]["C-02"].outcome == K.FAIL for t in new_dg)
    f24 = sum(gr[t]["C-01"].outcome == K.FAIL for t in new_tf)
    print(f"{rel}: on the 80 new cases, C-02 fails {f22} of 40, C-01 fails {f24} of 40")
    grow.setdefault("new80", {})[rel] = [f22, f24]
R["gate"] = {"n": len(base_gs), "spanish_offers": len(spanish_offers), "rows": grow,
             "new_tf_flows": dict(Counter(rowby[t]['flow'] for t in new_tf)),
             "new_dg_flows": dict(Counter(rowby[t]['flow'] for t in new_dg))}
# what the Spanish template defect would have cost had it shipped: Spanish offers per week at 10% traffic
es_week = sum(1 for t in offers if t["lang"] == "es") / 2
q2_weeks = (date(2027, 6, 30) - date(2027, 4, 19)).days / 7
print(f"\nApril Spanish offers {sum(1 for t in offers if t['lang'] == 'es')} in two weeks ({es_week:.1f} a week); "
      f"19 Apr to 30 Jun is {q2_weeks:.1f} weeks -> about {es_week * q2_weeks:.0f} offers without the disclosure at 10% "
      f"traffic, {es_week * q2_weeks * 10:.0f} at full traffic")
R["sidebar"] = {"es_offers_2wk": sum(1 for t in offers if t['lang'] == 'es'), "per_week": es_week, "weeks": q2_weeks,
                "est": es_week * q2_weeks}

# ---- H. census rates, offer census and fee draw
head("H1. Census rates, 1 to 14 April (every conversation)")
loanflow = [t for t in apr if t["flow"] in FEB.LOAN_FLOWS]
cens = {
    "MC-04 offer without approval sentence (C-04)": (len(FAILS(res, "C-04")), len(offers)),
    "MC-05 offer inside the window (C-03, offers)": (len(off_fail), len(offers)),
    "MC-12 closed queue, no callback time (C-05)": (len(FAILS(res, "C-05")), len(closed)),
    "MC-16 payoff reply differs from quote (C-07 reply side)": (side.get("reply", 0), quotes_ok),
    "MC-17 eligible borrower refused (C-03, refusals)": (len(ref_fail), len(hard)),
    "MC-19 tool on a loan other than the one named (C-02)": (len(c02), len(loanflow)),
    "MC-21 figure stated after a failed tool (C-01)": (len(c01), len(apr)),
    "payoff tool short by a day of interest (C-07 tool side)": (len(tool_f), quotes_ok),
    "citation to a superseded document (C-08)": (kinds["superseded document"], len(cited)),
}
alerts = {}
for k, (a, n) in cens.items():
    p = a / n if n else 0
    wk = n / 2
    al = int(binom.ppf(0.99, int(round(wk)), max(p, 1 / max(n, 1)))) + 1
    alerts[k] = al
    print(f"  {k:<58} {pct(a, n):<38} weekly alert at {al} or more")
R["census"] = {k: list(v) for k, v in cens.items()}
R["alerts"] = alerts

head("H2. MC-01 wrong hardship offer: the census over every stored conversation since 1 February")
feb = FEB.build()
risk = FEB.risk_fn(feb)
fr = [r for r in feb if r["status"] != "abandoned"]
dr = NBK.pps_quota(fr, "flow", FEB.QUOTAS, risk, seed=2026)
FEB.apply_facts(feb, [t for t, _, _ in dr])
mar = MAR.build()
tot_off, tot_wrong, per = 0, [], {}
for name, frame, rel in (("1-14 Feb", feb, "production"), ("1-14 Mar", mar, "production"), ("1-14 Apr", rows, "rc-0326-2")):
    hs = [A.render(r, rel) for r in frame if r["flow"] == "hardship"]
    hr, _ = S.run_all(hs)
    off = [t for t in hs if CC.spans(t, "draft_offer")]
    wrong = [t["trace_id"] for t in off if hr[t["trace_id"]]["C-03"].outcome == K.FAIL]
    wl = [t["trace_id"] for t in off if hr[t["trace_id"]]["C-02"].outcome == K.FAIL]
    logged = [r for r in frame if r["flow"] == "hardship" and r.get("offer_drafted")]
    discarded = [r for r in logged if r.get("tool_error")]
    per[name] = {"hardship": len(hs), "offers": len(off), "wrong": wrong, "wrong_loan": len(wl),
                 "logged": len(logged), "discarded": len(discarded)}
    print(f"  {name}: offer log {len(logged)} drafts, of which {len(discarded)} discarded after a failed tool call "
          f"(never shown to the borrower)")
    tot_off += len(off)
    tot_wrong += wrong
    print(f"  {name}: hardship {len(hs)}, offers {len(off)}, on the wrong loan {len(wl)}, wrong offers (C-03) {len(wrong)} {wrong}")
ub = upper_bound(len(tot_wrong), tot_off)
print(f"census: {pct(len(tot_wrong), tot_off)}; one-sided 95% bound {ub:.2%}; pilot estimate was one in 196 (bound 2.4%)")
print(f"offers per week {tot_off / 6:.0f}; offers needed for a 0.5% bound with {len(tot_wrong)} failures: "
      f"{__import__('truss.rates', fromlist=['traces_needed']).traces_needed(0.005, len(tot_wrong))}")
R["mc01"] = {"per": per, "offers": tot_off, "wrong": tot_wrong, "bound": ub}

head("H3. April fee draw (Thu 15 Apr): 200 fee conversations from 1-14 April, seed 2026, MC-02 v1.1")
ffr = [r for r in rows if r["flow"] == "fee_explanation" and r["status"] != "abandoned"]
drw = random.Random(2026).sample(ffr, 200)
drw_t = [by[r["trace_id"]] for r in drw]
wrong = [t for t in drw_t if t["meta"].get("wrong_fee")]
defer = [t for t in drw_t if t["meta"].get("outcome") == "deferred"]
print(f"fee frame {len(ffr)} (abandoned {sum(1 for r in rows if r['flow'] == 'fee_explanation') - len(ffr)} excluded); "
      f"wrong {pct(len(wrong), 200)}; one-sided bound {upper_bound(len(wrong), 200):.1%}; deferred {len(defer)} ({len(defer) / 2:.1f}%)")
print("  wrong by mode:", dict(Counter(tuple(t["truth"]) for t in wrong)), [t["trace_id"] for t in wrong])
cw = [t for t in wrong if K.verdict(res[t["trace_id"]]) == K.FAIL]
print(f"  code checks flag {len(cw)} of the {len(wrong)} wrong; the reading still decides all 200")
tw = sum(t["meta"].get("wrong_fee", False) for t in fee if rowby[t["trace_id"]]["status"] != "abandoned")
print(f"  fixture truth over the April fee frame: {pct(tw, len(ffr))}")
R["fee_draw"] = {"wrong": len(wrong), "deferred": len(defer), "ids": [t["trace_id"] for t in wrong],
                 "modes": dict(Counter("+".join(t["truth"]) for t in wrong)), "code_flag": len(cw),
                 "bound": upper_bound(len(wrong), 200), "frame_truth": [tw, len(ffr)]}

# ---- I. validation
head("I1. Validation: precision from reading every flag, recall from a read sample of 300 (50 per flow, seed 2026)")
samp = {t for t, _ in stratified([t for t in apr if rowby[t["trace_id"]]["status"] != "abandoned"], "flow",
                                  {f: 50 for f in flows}, seed=2026)}
val = {}
for v in ids:
    fl = FAILS(res, v)
    truth_v = {t["trace_id"] for t in apr if set(t["truth"]) & CC.TARGET[v]}
    if v == "C-08":
        truth_v |= {t["trace_id"] for t in apr if set(t["truth"]) & {"FM-24", "FM-07", "FM-19"} and t["trace_id"] in fl}
    pr = K.precision_recall(fl, samp, truth_v)
    fix = (len(fl & truth_v), len(truth_v))
    val[v] = {**pr, "fixture_recall": fix}
    p, rr = pr["precision"], pr["recall"]
    print(f"  {v} {S.by_id[v].name:<18} precision {p[0]}/{p[1]}  recall in sample {rr[0]}/{rr[1]}  "
          f"fixture recall {fix[0]}/{fix[1]}")
read_flags = len(set().union(*[FAILS(res, v) for v in ids]))
print(f"flags to read (distinct traces) {read_flags}; sample {len(samp)}")
R["validation"] = {v: {"precision": x["precision"], "recall": x["recall"], "fixture_recall": x["fixture_recall"],
                       "pw": x["precision_wilson"], "rw": x["recall_wilson"]} for v, x in val.items()}

head("I2. Mutation testing: plant a known failure in passing traces; does the check kill it?")
passing = [t for t in apr if K.verdict(res[t["trace_id"]]) == K.PASS]


def first(t, tool):
    return next((i for i, s in enumerate(t["spans"]) if s["tool"] == tool), None)


def mut(f):
    def g_(t):
        m = copy.deepcopy(t)
        return m if f(m) else None
    return g_


def m_drop_field(m):
    i = first(m, "get_fee_schedule") if first(m, "get_fee_schedule") is not None else first(m, "get_payoff_quote")
    if i is None or not CC.FIGURE_ACTION.search(m["reply"]):
        return False
    m["spans"][i]["result"].pop(next(iter(CC.RETURNS[m["spans"][i]["tool"]]["required"][1:2])), None)
    return True


def m_error(m):
    i = first(m, "get_fee_schedule") if first(m, "get_fee_schedule") is not None else first(m, "get_payoff_quote")
    if i is None or not CC.FIGURE_ACTION.search(m["reply"]):
        return False
    m["spans"][i].update(status="error", result={})
    return True


def m_other_loan(m):
    if not CC.DIGITS.search(m["message"]) or len(m["account"]["loans"]) < 2:
        return False
    other = next(x["loan_id"] for x in m["account"]["loans"] if x["loan_id"] != m["named_loan"])
    for s in m["spans"][1:]:
        if "loan_id" in s["args"]:
            s["args"]["loan_id"] = other
    return True


def m_recent(m):
    i = first(m, "draft_offer")
    if i is None:
        return False
    lr = CC.loan_rec(m, m["spans"][i]["args"]["loan_id"])
    e = date.fromisoformat(m["date"]) - timedelta(days=180)
    lr["relief"].append({"type": "deferral", "start": (e - timedelta(60)).isoformat(), "end": e.isoformat()})
    return True


def m_four(m):
    i = first(m, "draft_offer")
    if i is None:
        return False
    m["spans"][i]["args"]["months"] = 4
    return True


def m_drop_approval(m):
    if first(m, "draft_offer") is None:
        return False
    for s in CC.ALLOW:
        m["reply"] = m["reply"].replace(s, "")
    return True


def m_approved_claim(m):
    if first(m, "draft_offer") is None:
        return False
    for s in CC.ALLOW:
        m["reply"] = m["reply"].replace(s, "Your loan officer has approved this offer.")
    return True


def m_no_callback(m):
    i = first(m, "request_handoff")
    if i is None or m["spans"][i]["result"]["queue_open"]:
        return False
    m["reply"] = re.sub(r"I've asked one to call you back[^.]*\.|Le llamaremos[^.]*\.", "", m["reply"])
    return True


def m_seven(m):
    i = first(m, "request_handoff")
    if i is None or m["spans"][i]["result"]["queue_open"]:
        return False
    m["reply"] = m["reply"].replace("back at 8 a.m.", "back at 7 a.m.").replace("a las 8 a. m. ", "a las 7 a. m. ")
    return "7 a" in m["reply"]


def m_waive_flip(m):
    i = first(m, "get_fee_schedule")
    if i is None or m["spans"][i]["result"].get("waive_status") != "no" or not K.money(m["reply"]):
        return False
    m["spans"][i]["result"]["waive_status"] = "waive"
    return True


def m_ten_day(m):
    if "15-day grace" not in m["reply"] or first(m, "get_fee_schedule") is None:
        return False
    m["reply"] = m["reply"].replace("15-day grace", "10-day grace")
    return True


def m_pd_cent(m):
    mm = re.search(r"add \$([\d,.]+) for each", m["reply"])
    if not mm:
        return False
    v = K.Decimal(mm.group(1).replace(",", "")) + K.Decimal("0.01")
    m["reply"] = m["reply"].replace(f"add ${mm.group(1)}", f"add ${v:,.2f}")
    return True


def m_date_shift(m):
    i = first(m, "get_payoff_quote")
    if i is None or not K.dates(m["reply"]):
        return False
    d0 = K.dates(m["reply"])[0]
    for st_ in ("us", "num"):
        m["reply"] = m["reply"].replace(A.fmt_date(d0, st_), A.fmt_date(d0 - timedelta(days=1), st_))
    return True


def m_tool_day(m):
    i = first(m, "get_payoff_quote")
    if i is None:
        return False
    x = m["spans"][i]["result"]
    if "per_diem" not in x:
        return False
    x["payoff_amount"] = round(x["payoff_amount"] - x["per_diem"], 2)
    return True


def m_stale(m):
    if "HP-2027-04, section 4.3" not in m["reply"]:
        return False
    m["reply"] = m["reply"].replace("HP-2027-04, section 4.3", "HP-2026-09, section 4.2")
    return True


def m_invent(m):
    if not K.money(m["reply"]):
        return False
    m["reply"] = m["reply"].rstrip() + " A processing charge of $12.50 may also apply."
    return True


def m_invent_fee(m):
    return m["flow"] == "fee_explanation" and m_invent(m)


MUT = {"C-01": {"field dropped from return": m_drop_field, "tool error, reply unchanged": m_error},
       "C-02": {"tools called on the other loan": m_other_loan},
       "C-03": {"deferral 180 days before": m_recent, "four-month offer": m_four},
       "C-04": {"approval sentence deleted": m_drop_approval, "'has approved' claim": m_approved_claim},
       "C-05": {"callback sentence deleted": m_no_callback, "callback at 7 a.m.": m_seven},
       "C-06": {"tool says waive, reply defends": m_waive_flip, "10-day grace quoted": m_ten_day,
                "invented charge (fee replies)": m_invent_fee},
       "C-07": {"per diem +1 cent": m_pd_cent, "good-through a day early": m_date_shift,
                "tool payoff one day short": m_tool_day},
       "C-08": {"superseded citation": m_stale, "invented charge": m_invent}}
mres = {}
for v, ms in MUT.items():
    ver_ = S.by_id[v]
    sc = K.mutation_score(ver_, passing[:3000], {k: mut(f) for k, f in ms.items()},
                          upstream_fn=lambda m: {k: r for k, r in S.run(m).items()})
    mres[v] = sc
    for k, x in sc.items():
        print(f"  {v} {k:<32} applied {x['applied']:>4}  killed {x['killed']:>4}  survivors {len(x['survivors'])} "
              f"{x['survivors'][:2]}")
sv = [s_ for s_ in mres["C-06"]["tool says waive, reply defends"]["survivors"]]
print(f"  C-06 survivors share one phrasing: {dict(Counter('can' + chr(39) + 't be waived' in by[t]['reply'] for t in sv))} "
      f"(True = reply says the fee can't be waived)")
negsc = K.mutation_score(Sneg.by_id["C-06"], passing[:3000], {"tool says waive, reply defends": mut(m_waive_flip)},
                         upstream_fn=lambda m: Sneg.run(m))
x = negsc["tool says waive, reply defends"]
print(f"  C-06 with the negation rule: applied {x['applied']} killed {x['killed']}")
R["mutation_neg"] = [x["applied"], x["killed"]]
R["mutation"] = {v: {k: [x["applied"], x["killed"]] for k, x in sc.items()} for v, sc in mres.items()}

# ---- J. hours and dollars (ledger rates: lead and Ryan $85, officers $60)
head("J. Hours and dollars")
read_min = {"hardship": 10, "other": 3}
hard_n = flows["hardship"]
read_all = hard_n * 10 / 60 * 60 + (len(apr) - hard_n) * 3 / 60 * 85
print(f"reading every April conversation instead: {hard_n} hardship at 10 min ($60/h) + {len(apr) - hard_n:,} others at "
      f"3 min ($85/h) = ${read_all:,.0f} a fortnight")
samp_h = sum(1 for t in samp if by[t]["flow"] == "hardship")
flag_h = sum(1 for t in set().union(*[FAILS(res, v) for v in ids]) if by[t]["flow"] == "hardship")
flag_o = read_flags - flag_h
plan = [("Ryan: C-01, C-02, C-05, C-07, schemas (Mon 5 - Fri 9 Apr)", 22, 85),
        ("you: C-06, C-08, suite, composition, validation code", 18, 85),
        ("Grace: C-03 and C-04 rules, boundary cases (two sessions)", 3, 60),
        ("Victor: approval wordings and the window ruling (Tue 6 Apr)", 1, 85),
        (f"validation reading: sample {len(samp)} ({samp_h} hardship at 10 min, rest at 3 min)",
         None, None),
        (f"validation reading: {read_flags} flags at 2 min ({flag_h} hardship by Grace's team)", None, None)]
rows_h = []
tot_h = tot_d = 0
for label, h, rate in plan:
    if h is None and label.startswith("validation reading: sample"):
        d_ = samp_h * 10 / 60 * 60 + (len(samp) - samp_h) * 3 / 60 * 85
        h = samp_h * 10 / 60 + (len(samp) - samp_h) * 3 / 60
    elif h is None:
        d_ = flag_h * 2 / 60 * 60 + flag_o * 2 / 60 * 85
        h = read_flags * 2 / 60
    else:
        d_ = h * rate
    rows_h.append((label, h, d_))
    tot_h += h
    tot_d += d_
    print(f"  {label:<78} {h:>5.1f} h  ${d_:>7,.0f}")
print(f"  total {tot_h:.1f} h, ${tot_d:,.0f}; running the eight checks over a fortnight: {secs:.1f} s of one laptop core")
R["hours"] = {"rows": rows_h, "total_h": tot_h, "total_d": tot_d, "read_all": read_all}

# ---- K. check coverage
head("K. Check coverage, taxonomy v0.3")
t03 = T.Taxonomy.from_json((HERE.parents[0] / "ch07" / "out" / "taxonomy-v0.3.json").read_text())
CH7 = {"FM-01": [3], "FM-03": [3], "FM-04": [1, 3], "FM-06": [1, 3], "FM-07": [3], "FM-08": [3],
       "FM-11": [3], "FM-12": [3], "FM-14": [3], "FM-15": [3], "FM-16": [3], "FM-17": [3], "FM-18": [3],
       "FM-19": [3], "FM-20": [3], "FM-21": [3], "FM-22": [1], "FM-24": [1]}
CH9 = copy.deepcopy(CH7)
for v in ids:
    for m in S.by_id[v].modes:
        if m in t03.modes:
            CH9.setdefault(m, []).append(1)
c7, c9 = T.check_coverage(t03, CH7), T.check_coverage(t03, CH9)
print(f"end of Chapter 8: {c7['with_check']}/{c7['modes']} = {c7['share']:.0%}; missing {c7['missing']}")
print(f"end of Chapter 9: {c9['with_check']}/{c9['modes']} = {c9['share']:.0%}; missing {c9['missing']}")
for v in ids:
    print(f"  {v} {S.by_id[v].name:<18} modes {S.by_id[v].modes} cards {S.by_id[v].cards} owner {S.by_id[v].owner}")
R["coverage"] = {"ch8": [c7["with_check"], c7["modes"], c7["missing"]], "ch9": [c9["with_check"], c9["modes"], c9["missing"]]}
R["coverage_checks"] = CH9
(OUT / "lab.json").write_text(json.dumps(R, indent=1, default=str))
print("written out/lab.json")
