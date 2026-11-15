"""Chapter 22 lab: does the study judge's written critique predict its verdict errors?
Reads the cached REAL runs (claude-haiku-4-5-20251001); traffic and truth are SIMULATED (fixture.py).
Writes out/lab.json. Run: python3 lab.py"""
import json
from collections import Counter

from common import *  # noqa: F401,F403
import common as C

L = {}
print("Chapter 22 lab: judging the judge's explanations")
S = C.STUDY
print(f"study set {len(S)} fee traces, {S[0]['trace_id']} to {S[-1]['trace_id']}; dev {len(C.DEV)}, held-out {len(C.TEST)}")
print(f"  gold fail {sum(t['truth'] == 'fail' for t in S)}; random stratum {sum(t['stratum'] == 'random' for t in S)} "
      f"(fail {sum(t['truth'] == 'fail' for t in S if t['stratum'] == 'random')}); near-anniversary waivers {sum(t['edge'] for t in S)}; "
      f"HB-2027-12 trigger payments {sum(t['hb'] for t in S)}")
L["set"] = {"n": len(S), "fail": sum(t["truth"] == "fail" for t in S), "edge": sum(t["edge"] for t in S),
            "random": sum(t["stratum"] == "random" for t in S), "random_fail": sum(t["truth"] == "fail" for t in S if t["stratum"] == "random")}

print("\n1. Real calls (cached)")
tot = []
for n in C.J.ORDER:
    recs = list(C.J.load(n).values())
    tot += recs
    u = C.llm.usage(recs)
    print(f"  {n:10s} {u['calls']:4d} calls  in {u['in']:>9,}  out {u['out']:>8,}  ${u['cost']:.2f}")
u = C.llm.usage(tot)
print(f"  all        {u['calls']:4d} calls  in {u['in']:>9,}  out {u['out']:>8,}  ${u['cost']:.2f}  (+ replies, see gen.py)")
L["calls"] = u

print("\n2. Drafting the rules on the development set (critiques read after each draft)")
dev_ids = {t["trace_id"] for t in C.DEV}
L["drafts"] = {}
for n, label in (("r1", "draft 1: 'fewer than twelve calendar months'"), ("r1b_dev", "draft 2: cut-off with a worked example"),
                 ("r2_dev", "draft 3: + judge the status, not the explanation"), ("v2_dev", "draft 4 (shipped to the study)")):
    R = C.J.load(n)
    ids = sorted(i for i in R if i in dev_ids)
    tb = C.table([C.BY_ID[i]["truth"] for i in ids], [C.J.verdict(R[i]["text"]) for i in ids], [C.BY_ID[i]["kind"] for i in ids])
    ex = sum("2027-02-09" in R[i]["text"] and C.BY_ID[i]["fee_date"] != "2028-02-09" for i in ids)
    print(f"  {label:52s} TPR {tb['tp']}/{tb['P']}  TNR {tb['tn']}/{tb['N']}  example date copied into {ex} critiques")
    L["drafts"][n] = {"tp": tb["tp"], "P": tb["P"], "tn": tb["tn"], "N": tb["N"], "example_copied": ex}
R1 = C.J.load("r1")
fa = [i for i in R1 if C.J.verdict(R1[i]["text"]) == "fail" and C.BY_ID[i]["truth"] == "pass"]
print(f"  draft 1 on all 300: {len(fa)} false alarms of {sum(C.BY_ID[i]['truth'] == 'pass' for i in R1)} permitted replies")
L["r1_all_fa"] = len(fa)

print("\n3. The study judge (draft 4, critique first) on the 300")
rs = C.rows("v2")
L["v2"] = {}
for part, sel in (("dev", lambda r: r["split"] == "dev"), ("test", lambda r: r["split"] == "test"),
                  ("random", lambda r: r["stratum"] == "random"), ("test random", lambda r: r["split"] == "test" and r["stratum"] == "random")):
    a = [r for r in rs if sel(r)]
    tb = C.table([r["truth"] for r in a], [r["verdict"] for r in a], [r["kind"] for r in a])
    print(f"  {part:12s} n={len(a):3d} TPR {tb['tp']}/{tb['P']} ({C.ci(tb['tpr_ci'])})  TNR {tb['tn']}/{tb['N']} ({C.ci(tb['tnr_ci'])})  "
          f"kappa {tb['kappa']:.3f}  errors {sum(r['err'] for r in a)}  cannot tell {tb['abstain_pos'] + tb['abstain_neg']}")
    L["v2"][part] = {k: tb[k] for k in ("tp", "P", "tn", "N", "tpr", "tnr", "tpr_ci", "tnr_ci", "kappa")}
    L["v2"][part]["errors"] = sum(r["err"] for r in a)
test = [r for r in rs if r["split"] == "test"]
ek = Counter((r["kind"], r["edge"]) for r in test if r["err"])
print("  held-out errors by kind (near-anniversary marked *):", ", ".join(f"{k}{'*' if e else ''} {n}" for (k, e), n in ek.most_common()))
L["test_err_kinds"] = {f"{k}{'*' if e else ''}": n for (k, e), n in ek.items()}

print("\n4. Rationale features against verdict error")
long_words = C.median([r["words"] for r in rs if r["split"] == "dev"])
C.add_flags(rs, long_words)
print(f"  length threshold = development median, {long_words} words")
names = {"f_long": "longer than the dev median", "f_hedge": "one or more hedges", "f_self": "visible self-correction",
         "f_low_conv": "reader rates it 3 or less of 5", "f_contra": "argues the other verdict or unclear",
         "f_bad_date": "quotes a date not in the trace", "f_window": "window claim wrong (code check)",
         "f_cutoff": "cut-off claim wrong (code check)", "f_wdate": "waiver date claim wrong", "f_status": "status claim wrong (code recomputes status)"}
L["assoc"] = {}
for f, label in names.items():
    line = []
    for part in ("dev", "test"):
        a = [r for r in rs if r["split"] == part]
        x = C.RA.association([r[f] for r in a], [r["err"] for r in a])
        line.append(f"{part} {x['present_err']}/{x['present']} vs {x['absent_err']}/{x['absent']}")
        L["assoc"].setdefault(f, {})[part] = x
    print(f"  {label:42s} " + "   ".join(line))
conv = Counter(r["convincing"] for r in rs)
print("  reader 'convincing' scores on the 300:", dict(sorted(conv.items(), key=lambda kv: (kv[0] is None, kv[0]))))
for e in (0, 1):
    a = [r["convincing"] for r in rs if r["err"] == e and r["convincing"]]
    print(f"    mean when verdict {'wrong' if e else 'right'}: {sum(a) / len(a):.3f} (n {len(a)})")
L["conv_mean"] = {str(e): sum(r["convincing"] for r in rs if r["err"] == e and r["convincing"]) / sum(1 for r in rs if r["err"] == e and r["convincing"]) for e in (0, 1)}
cc = Counter(r["consistency"] for r in rs)
print("  consistency of critique and verdict line:", dict(cc))
L["consistency"] = dict(cc)
chk = sum(1 for r in rs if r["claims_checked"])
print(f"  critiques making at least one checkable claim: {chk}/300; with a window claim: {sum('window' in r['claims_checked'] for r in rs)}")
L["checkable"] = chk

BUDGET = 0.25
print(f"\n5. Flag rules fitted on development (budget: {BUDGET:.0%} of dev flagged), scored on held-out")
dev = [r for r in rs if r["split"] == "dev"]
L["rules"] = {}
fams = dict(C.FAMILIES)
fams["all three"] = sorted(set(sum(C.FAMILIES.values(), [])))
for fam, feats in fams.items():
    fit = C.RA.fit_flag_rule(dev, feats, BUDGET)
    ev = C.RA.evaluate_flag(test, fit["rule"], production=lambda r: r["stratum"] == "random")
    print(f"  {fam:12s} rule {fit['rule'] or ['(nothing helps)']}: dev {fit['caught']}/{fit['errors']} at {fit['flagged']}/{fit['n']}; "
          f"held-out catches {ev['caught']}/{ev['errors']} = {C.pct(ev['catch']) if ev['errors'] else '-'} ({C.ci(ev['catch_ci'])}) "
          f"flagging {ev['flagged']}/{ev['n']} = {C.pct(ev['flag_share'])}; random stratum flagged {ev['prod_flagged']}/{ev['prod_n']} = {C.pct(ev['prod_flag_share'])}, "
          f"its errors caught {ev['prod_caught']}/{ev['prod_errors']}")
    L["rules"][fam] = {"fit": fit, "eval": ev}
for f in ("f_contra", "f_window"):
    ev = C.RA.evaluate_flag(test, [f], production=lambda r: r["stratum"] == "random")
    print(f"  {names[f]} alone: held-out {ev['caught']}/{ev['errors']} ({C.ci(ev['catch_ci'])}) flagging {ev['flagged']}/{ev['n']}; random {ev['prod_flagged']}/{ev['prod_n']}, precision {ev['caught']}/{ev['flagged']}")
    L["rules"][f] = {"eval": ev}
curve = {}
for fam, feats in fams.items():
    curve[fam] = []
    for b in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30):
        fit = C.RA.fit_flag_rule(dev, feats, b)
        ev = C.RA.evaluate_flag(test, fit["rule"], production=lambda r: r["stratum"] == "random")
        curve[fam].append({"budget": b, "rule": fit["rule"], "catch": ev["caught"], "errors": ev["errors"], "prod_share": ev["prod_flag_share"], "share": ev["flag_share"]})
    print(f"  curve {fam:12s} " + "  ".join(f"{c['budget']:.2f}:{c['catch']}/{c['errors']}@{C.pct(c['prod_share'])}" for c in curve[fam]))
L["curve"] = curve
ev = C.RA.evaluate_flag(test, ["f_status"], production=lambda r: r["stratum"] == "random")
print(f"  status recompute (code decides the status itself): held-out {ev['caught']}/{ev['errors']} flagging {ev['flagged']}/{ev['n']}; random {ev['prod_flagged']}/{ev['prod_n']}")
L["rules"]["status recompute"] = {"eval": ev}

print("\n6. Right for the wrong reason, wrong for the right one (held-out)")
rw = [r for r in test if not r["err"] and r["claims_wrong"]]
wr = [r for r in test if r["err"] and r["claims_checked"] and not r["claims_wrong"]]
nochk = [r for r in test if r["err"] and not r["claims_checked"]]
print(f"  right verdict, a checkable claim wrong: {len(rw)} of {sum(not r['err'] for r in test)} right verdicts; kinds {dict(Counter(r['kind'] for r in rw))}")
print(f"  wrong verdict, every checkable claim right: {len(wr)}; wrong verdict, no checkable claim: {len(nochk)}")
L["rwr"] = {"right_wrong_claim": len(rw), "right_total": sum(not r["err"] for r in test), "wrong_claims_right": len(wr), "wrong_no_claim": len(nochk),
            "rw_kinds": dict(Counter(r["kind"] for r in rw))}

print("\n7. An authority sentence in the reply, against a plain repeat (100 held-out traces)")
ids = sorted(C.J.load("cue"))
V2, B, CU = C.J.load("v2"), C.J.load("cue_base"), C.J.load("cue")
base = [C.J.verdict(V2[i]["text"]) for i in ids]
rep = [C.J.verdict(B[i]["text"]) for i in ids]
cue = [C.J.verdict(CU[i]["text"]) for i in ids]
import re
ack = [bool(re.search(r"checked|rely|full account history|assur", C.J.strip_verdict(CU[i]["text"]), re.I)) for i in ids]
ce = C.RA.cue_effect(base, rep, cue, ack)
print(f"  plain repeat flips {ce['noise_flips']}/100; with the cue {ce['cue_flips']}/100 ({ce['toward']} toward pass, {ce['away']} away); "
      f"critiques mentioning the cue {ce['ack_any']}/100")
L["cue"] = ce
fl = [i for i, a, b in zip(ids, base, rep) if a != b]
print(f"  repeat flips by kind: {dict(Counter(C.BY_ID[i]['kind'] + ('*' if C.BY_ID[i]['edge'] else '') for i in fl))}")
L["repeat_flip_kinds"] = dict(Counter(C.BY_ID[i]["kind"] + ("*" if C.BY_ID[i]["edge"] else "") for i in fl))

print("\n8. What explanations cost")
VO = C.J.load("vonly")
ec = C.RA.explanation_cost(sum(r["out"] for r in V2.values()), sum(r["out"] for r in VO.values()), 300, C.PRICE_OUT, C.MONTHLY_FEE)
uv2, uvo = C.llm.usage(V2.values()), C.llm.usage(VO.values())
print(f"  critique adds {ec['extra_tokens_per_call']:.1f} output tokens a call: ${ec['extra_per_call']:.5f} a call, ${ec['extra_per_month']:.2f} a month at {C.MONTHLY_FEE:,} fee conversations")
print(f"  per call all-in: critique ${uv2['cost'] / 300:.5f}, verdict only ${uvo['cost'] / 300:.5f}; month ${uv2['cost'] / 300 * C.MONTHLY_FEE:.2f} vs ${uvo['cost'] / 300 * C.MONTHLY_FEE:.2f}")
med = lambda R: sorted(r["latency"] for r in R.values())[len(R) // 2]
print(f"  median latency: critique {med(V2):.2f} s, verdict only {med(VO):.2f} s")
L["cost"] = {"extra_tokens": ec["extra_tokens_per_call"], "extra_month": ec["extra_per_month"], "v2_call": uv2["cost"] / 300, "vo_call": uvo["cost"] / 300,
             "v2_month": uv2["cost"] / 300 * C.MONTHLY_FEE, "vo_month": uvo["cost"] / 300 * C.MONTHLY_FEE, "lat_v2": med(V2), "lat_vo": med(VO)}
for fam in ("claim check", "consistency", "style", "f_window"):
    share = L["rules"][fam]["eval"]["prod_flag_share"]
    rc = C.RA.review_cost(share, C.MONTHLY_FEE, C.READ_MIN, C.OFFICER_RATE)
    print(f"  reading the {fam} flags: {rc['reviews']:.0f} verdicts a month, {rc['minutes'] / 60:.1f} officer hours, ${rc['dollars']:,.0f}")
    L["rules"][fam]["review"] = rc

print("\n9. The critique that argued for a verdict it did not return")
ex = [r for r in rs if r["consistency"] == "contradicts"]
for r in ex:
    print(f"  {r['id']} {r['kind']} truth {r['truth']} verdict {r['verdict']}")
pick = next(r for r in ex if r["id"] == "t-256606")
t = C.BY_ID[pick["id"]]
print(f"  {pick['id']}: fee {t['fee_date']}, waiver {t['waiver']}, cut-off {C.RA.cutoff(t['fee_date'])}, code window {C.window(t)}, truth {t['truth']}, verdict {pick['verdict']}")
print("  critique: " + pick["text"].replace("**Critique:**", "").strip())
L["contradicts"] = [r["id"] for r in ex]

print("\n10. The debugging surface pays: the window result from code as an input (held-out 200)")
W = C.J.load("window_in")
ids = sorted(W)
tb = C.table([C.BY_ID[i]["truth"] for i in ids], [C.J.verdict(W[i]["text"]) for i in ids], [C.BY_ID[i]["kind"] for i in ids])
errs = [i for i in ids if C.J.verdict(W[i]["text"]) != C.BY_ID[i]["truth"]]
print(f"  TPR {tb['tp']}/{tb['P']} ({C.ci(tb['tpr_ci'])})  TNR {tb['tn']}/{tb['N']} ({C.ci(tb['tnr_ci'])})  kappa {tb['kappa']:.3f}  errors {len(errs)} "
      f"(by kind {dict(Counter(C.BY_ID[i]['kind'] for i in errs))}); cannot tell {tb['abstain_pos'] + tb['abstain_neg']}")
rand = [i for i in ids if C.BY_ID[i]["stratum"] == "random"]
print(f"  random stratum errors {sum(C.J.verdict(W[i]['text']) != C.BY_ID[i]['truth'] for i in rand)}/{len(rand)} (was {L['v2']['test random']['errors']}/83)")
L["window_in"] = {k: tb[k] for k in ("tp", "P", "tn", "N", "tpr_ci", "tnr_ci", "kappa")}
L["window_in"]["errors"] = len(errs)
L["window_in"]["random_errors"] = sum(C.J.verdict(W[i]["text"]) != C.BY_ID[i]["truth"] for i in rand)

json.dump(L, open(C.F.__file__.replace("fixture.py", "out/lab.json"), "w"), indent=1, default=str)
