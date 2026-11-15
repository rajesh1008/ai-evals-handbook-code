"""Chapter 16 lab: the MC-02 judge, measured. Reads the cached REAL model runs (gen.py, judges.py,
agent.py) over the SIMULATED fixture and prints every number the chapter uses. Writes out/lab.json."""
import json
from collections import Counter

from common import (DEV, TEST, BUGS, NORMAL, RES, F, J, TJ, BY_ID, agent, gen, llm, verdicts, score, usage, line)

OUT = {}


def head(s):
    print("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)


head("1. Fixture (SIMULATED): the October fortnight and fee-judge-v1")
frame = F.frame()
k = Counter(t["kind"] for t in frame)
print(f"fee conversations Mon 4 to Sun 17 Oct 2027: {len(frame)} ({frame[0]['trace_id']} to {frame[-1]['trace_id']})")
print("kinds:", dict(k.most_common()))
v11 = sum(t["v11"] == "fail" for t in frame); tru = sum(t["truth"] == "fail" for t in frame)
print(f"MC-02 v1.1 fail: {v11} ({v11 / len(frame):.1%}); wrong for the borrower incl. fee-tool 3.4 bug: {tru} ({tru / len(frame):.1%})")
bug_dates = Counter(t["date"] for t in frame if t["kind"] == "tool_bug")
print("tool_bug traces by day:", dict(sorted(bug_dates.items())))
for name, s in (("dev", DEV), ("test", TEST)):
    print(f"{name}: {len(s)}  v1.1 fail {sum(t['v11'] == 'fail' for t in s)}  strata {dict(Counter(t['stratum'] for t in s))}  kinds {dict(Counter(t['kind'] for t in s).most_common())}")
R = gen.replies()
words = [len(R[t["trace_id"]]["text"].split()) for t in TEST]
print(f"reply words on test (REAL, written by the small model): median {sorted(words)[100]}, range {min(words)} to {max(words)}")
OUT["fixture"] = {"n": len(frame), "kinds": dict(k), "v11_fail": v11, "truth_fail": tru,
                  "dev_fail": sum(t["v11"] == "fail" for t in DEV), "test_fail": sum(t["v11"] == "fail" for t in TEST)}

head("2. Reply-only reading (J0): the judge without the span")
for nm, s in (("dev_j0", DEV), ("test_j0", TEST)):
    r = score(nm, s); print(line(nm, r))
    print("   verdicts:", dict(Counter(r["pred"].values())))
    OUT[nm] = {k_: r[k_] for k_ in ("tpr", "tnr", "kappa", "cm", "n")}

head("3. Dev iteration: the card question as written (v0) and with rules (v1), 100 dev traces")
for nm in ("dev_v0", "dev_v1"):
    r = score(nm, DEV); print(line(nm, r))
    for kk, row in sorted(r["by_kind"].items()):
        print(f"     {kk:13s} {row}")
    OUT[nm] = {k_: r[k_] for k_ in ("tpr", "tnr", "kappa", "cm", "n", "by_kind")}
v0 = verdicts("dev_v0")
reason_fp = [t["trace_id"] for t in DEV if t["kind"] == "right_no" and v0[t["trace_id"]] == "fail"]
nr = Counter(t["history"]["reason"] for t in DEV if t["trace_id"] in reason_fp)
print(f"v0 false alarms on right_no: {len(reason_fp)}, by the reason the reply gave: {dict(nr)}")
print(f"v0 on tool errors (X_invent): {dict(Counter(v0[t['trace_id']] for t in DEV if t['kind'] == 'X_invent'))}")
verdict_first = sum(1 for t in DEV if RES['dev_v0'][t['trace_id']]['text'].lstrip('`json \n').startswith('{'))
print(f"v0 replies that put the verdict before any reasoning: {verdict_first} of {len(DEV)}")
OUT["v0_reason_fp"] = dict(nr); OUT["v0_verdict_first"] = verdict_first

head("4. Held-out test, 200 traces, judge v1 (small model, run 1 of 3)")
r = score("test_v1_small_r0", TEST); print(line("test_v1_small_r0", r))
print(f"   precision of a fail verdict: {r['precision']:.3f}; confusion {r['cm']}")
for kk, row in sorted(r["by_kind"].items()):
    print(f"     {kk:13s} {row}")
wrong = [(i, BY_ID[i]["kind"], p) for i, p in r["pred"].items() if p != BY_ID[i]["v11"]]
print("   disagreements with the v1.1 label:", wrong)
OUT["test_v1"] = {k_: r[k_] for k_ in ("tpr", "tnr", "tpr_ci", "tnr_ci", "kappa", "cm", "n", "precision", "by_kind")}
OUT["test_v1_wrong"] = wrong
r0 = score("test_v0", TEST); print(line("test_v0 (for contrast)", r0))
OUT["test_v0"] = {k_: r0[k_] for k_ in ("tpr", "tnr", "kappa", "cm")}
bt = [t for t in TEST if t["kind"] == "tool_bug"]
print(f"   test traces carrying the fee-tool 3.4 error: {len(bt)}; judge v1 verdicts {dict(Counter(r['pred'][t['trace_id']] for t in bt))} (v1.1 label pass, borrower label fail)")

head("5. Model choice on the same 200 test traces")
OUT["models"] = {}
for nm, label in (("test_v1_small_r0", "small"), ("test_v1_large", "large"), ("test_v1_think", "small + extended thinking")):
    r = score(nm, TEST); u = usage(RES[nm].values())
    print(line(label, r))
    print(f"     tokens in/out per call {u['in_per']:.0f}/{u['out_per']:.0f}  cost per call ${u['per_call']:.5f}  total ${u['cost']:.3f}  latency p50 {u['p50']:.2f} s p95 {u['p95']:.2f} s")
    OUT["models"][label] = {"tpr": r["tpr"], "tnr": r["tnr"], "tpr_ci": r["tpr_ci"], "tnr_ci": r["tnr_ci"], "kappa": r["kappa"],
                            "cm": r["cm"], "per_call": u["per_call"], "p50": u["p50"], "p95": u["p95"],
                            "in_per": u["in_per"], "out_per": u["out_per"], "cost": u["cost"],
                            "wrong": [(i, BY_ID[i]["kind"], p) for i, p in r["pred"].items() if p != BY_ID[i]["v11"]]}
    print("     disagreements:", OUT["models"][label]["wrong"])

head("6. Repeats: three runs of the small judge on the same 200 traces")
runs = [[verdicts(f"test_v1_small_r{i}")[t["trace_id"]] for t in TEST] for i in range(3)]
fl = TJ.flips(runs)
print(f"items whose verdict changed across three runs: {fl['flipped']} of {fl['items']} ({fl['rate']:.1%})")
print("   flipped:", [(TEST[i]["trace_id"], TEST[i]["kind"], [r_[i] for r_ in runs]) for i in fl["where"]])
for i in range(3):
    print(line(f"run {i + 1}", score(f"test_v1_small_r{i}", TEST)))
maj = dict(zip([t["trace_id"] for t in TEST], TJ.majority(runs)))
rm = score("majority", TEST, res=maj); print(line("majority of three", rm))
OUT["flips"] = {"flipped": fl["flipped"], "n": fl["items"], "where": [TEST[i]["trace_id"] for i in fl["where"]]}
OUT["majority"] = {"tpr": rm["tpr"], "tnr": rm["tnr"], "kappa": rm["kappa"], "cm": rm["cm"]}
OUT["runs"] = [{k_: score(f"test_v1_small_r{i}", TEST)[k_] for k_ in ("tpr", "tnr", "cm")} for i in range(3)]

head("7. Pairwise against absolute, 80 test traces with a second reply (REAL)")
con, eq = gen.pair_plan()
A = gen.alt_replies()
pv = verdicts("pairs_small", field="better")
res = {}
for t in con + eq:
    i = t["trace_id"]
    res[i] = TJ.pair_outcome(pv.get(i + ":OA"), pv.get(i + ":AO"))
cc = Counter()
for t in con:
    right = "original" if t["kind"] in F.PASS_KINDS else "other"
    o = res[t["trace_id"]]
    cc["right reply preferred" if o == right else "wrong reply preferred" if o in ("original", "other") else o] += 1
print("contrast pairs (one right, one wrong reply), 40:", dict(cc))
ce = Counter()
for t in eq:
    o = res[t["trace_id"]]
    ce["longer preferred" if o == "other" else "shorter preferred" if o == "original" else o] += 1
print("equal pairs (both right, one about twice as long), 40:", dict(ce))
lens = [(len(R[t['trace_id']]['text'].split()), len(A[t['trace_id']]['text'].split())) for t in eq]
print(f"   equal pairs: median words {sorted(a for a, _ in lens)[20]} against {sorted(b for _, b in lens)[20]}")
raw = Counter((pv.get(t["trace_id"] + ":OA"), pv.get(t["trace_id"] + ":AO")) for t in eq)
print("   raw (original-first, original-second) answers on equal pairs:", dict(raw))
# absolute: judge v1 on both replies of each pair
av = verdicts("alt_v1_small")
ov = verdicts("test_v1_small_r0")
ok_con = sum(1 for t in con if ov[t["trace_id"]] == t["v11"] and av[t["trace_id"]] == ("pass" if t["kind"] in F.FAIL_KINDS else "fail"))
ok_eq = sum(1 for t in eq if ov[t["trace_id"]] == "pass" and av[t["trace_id"]] == "pass")
print(f"absolute v1 judge gets both replies right: contrast {ok_con} of 40, equal {ok_eq} of 40")
pu = usage(RES["pairs_small"].values())
print(f"pairwise cost: {pu['calls']} calls ${pu['cost']:.3f} (two orders per pair); latency p50 {pu['p50']:.2f} s")
OUT["pairs"] = {"contrast": dict(cc), "equal": dict(ce), "abs_contrast": ok_con, "abs_equal": ok_eq,
                "raw_equal": {f"{a}|{b}": n for (a, b), n in raw.items()}, "cost": pu["cost"], "calls": pu["calls"]}

head("8. The fee-tool 3.4 error: span-only judges against the agent judge (MC-02 v1.2)")
bug_ids = [t["trace_id"] for t in BUGS]
for nm in ("bugs_v1_small", "bugs_v1_large"):
    v = verdicts(nm); print(f"{nm}: on 20 tool_bug traces {dict(Counter(v[i] for i in bug_ids))}")
OUT["agent"] = {}
for m, calc, label in ((llm.SMALL, False, "agent small"), (llm.LARGE, False, "agent large"), (llm.SMALL, True, "agent small + days_between")):
    d = agent.run(m, calc=calc)
    if len(d) < 60:
        print(f"{label}: only {len(d)} of 60 cached; run python3 agent.py run"); continue
    sets_ = {"bugs": BUGS, "normal": NORMAL}
    rr = {}
    for sname, ts in sets_.items():
        res_ = {t["trace_id"]: J.verdict(d[t["trace_id"]]["text"]) for t in ts}
        rr[sname] = score(label, ts, truth_key="truth", res=res_)
    u = usage(d.values()); calls = Counter(len(r_["tool_calls"]) for r_ in d.values())
    names = Counter(c["name"] for r_ in d.values() for c in r_["tool_calls"])
    caught = rr["bugs"]["cm"]["tp"]
    print(f"{label}: tool_bug caught {caught}/20; other 40: " + line("", rr["normal"]).strip())
    print(f"     tool calls per trace {dict(sorted(calls.items()))} by name {dict(names)}; cost per trace ${u['per_call']:.4f}; "
          f"tokens in/out per trace {u['in_per']:.0f}/{u['out_per']:.0f}; latency p50 {u['p50']:.1f} s p95 {u['p95']:.1f} s")
    wrong = [(t["trace_id"], t["kind"], rr["normal"]["pred"][t["trace_id"]]) for t in NORMAL if rr["normal"]["pred"][t["trace_id"]] != t["truth"]]
    print("     wrong on the other 40:", wrong)
    OUT["agent"][label] = {"caught": caught, "normal_cm": rr["normal"]["cm"], "normal_wrong": wrong, "per_call": u["per_call"],
                           "p50": u["p50"], "p95": u["p95"], "in_per": u["in_per"], "out_per": u["out_per"], "cost": u["cost"],
                           "calls_dist": dict(calls), "by_name": dict(names)}

head("9. A month of judging every fee conversation, against reading them")
month_n = round(len(frame) * 30 / 14)
fail_rate = OUT["fixture"]["v11_fail"] / len(frame)
print(f"fee conversations per 30 days at the fortnight's pace: {month_n}; v1.1 fail rate {fail_rate:.1%}")
OUT["month"] = {"n": month_n}
for label, per in (("small judge", OUT["models"]["small"]["per_call"]), ("large judge", OUT["models"]["large"]["per_call"]),
                   ("agent large", OUT["agent"].get("agent large", {}).get("per_call", float("nan")))):
    m = TJ.month(month_n, per, fail_rate, read_minutes=2.0, reader_rate=60.0)
    print(f"{label:12s} judge ${m['judge_cost']:.2f}  ordered reads {m['ordered_reads']:.0f} costing ${m['read_ordered_cost']:.0f}  "
          f"together ${m['judge_plus_reads']:.0f}  reading everything ${m['read_everything']:.0f}")
    OUT["month"][label] = m

head("10. Entry to the monitoring tier (truss.judge.admit)")
spec = TJ.JudgeSpec("MC-02", "1.1", J.CARD_Q, ["(rules as in judges.RULES_V1)"], model=llm.SMALL, version="fee-judge v1")
t1 = OUT["test_v1"]
for role in ("order", "decide"):
    a = TJ.admit(spec, t1, role=role); print(role, a); OUT[f"admit_{role}"] = a
tot = usage([r_ for v in RES.values() for r_ in v.values()])
print(f"\nall judge calls in this lab: {tot['calls']} calls, {tot['in']:,} tokens in, {tot['out']:,} out, about ${tot['cost']:.2f} at the assumed prices")
OUT["total_judge_calls"] = tot
json.dump(OUT, open(llm.OUT / "lab.json", "w"), indent=1, default=str)
