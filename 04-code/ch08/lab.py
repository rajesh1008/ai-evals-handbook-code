"""Chapter 8 lab: from failure modes to metrics.
A registry and the suite; B the wrong-fee metric, drafted, disputed and amended; C the scale study;
D hierarchy; E composites; F metric cards; G Truss v1's first before/after tables and the fee gate; H hours.
Run: python3 lab.py   (writes out/lab.json and out/metric-cards.md)"""
import json
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
import truss  # noqa: E402
from truss import metrics as M  # noqa: E402
from truss.rates import traces_needed, upper_bound, wilson  # noqa: E402
from truss.taxonomy import kappa  # noqa: E402
import february as FEB  # noqa: E402
import march as MAR  # noqa: E402
import suite as SU  # noqa: E402
import compass_sim as C  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
R = {"truss": truss.__version__}


def head(s):
    print(f"\n== {s}")


def pct(k, n):
    lo, hi = wilson(k, n)
    return f"{k} in {n} ({k / n:.1%}, Wilson {lo:.1%} to {hi:.1%})"


# ---- A. registry
head("A. The registry: one metric per active v0.3 failure mode")
feb = FEB.build()
reg = SU.registry(feb)
print(f"Truss {truss.__version__}; taxonomy v{SU.TAX['version']} digest {SU.TAX['digest']}")
tiers = reg.by_tier()
kinds = Counter(c.kind for c in reg.cards.values())
for cid, c in reg.cards.items():
    ev = ", ".join(reg.evidence.get(c.modes[0], [])[:1]) if c.modes else "-"
    print(f"{cid}  {c.tier:<7} {c.kind:<9} {','.join(c.modes) or '-':<19} {c.name[:58]:<58} {ev}")
print("by tier:", {k: len(v) for k, v in tiers.items()}, " by kind:", dict(kinds))
print("active modes with no metric:", reg.unmetered() or "none")
print("refused:")
for cid, name, why in reg.refused:
    print(f"  {cid} {name}: {'; '.join(why)}")
R["registry"] = {"cards": {k: {"name": c.name, "modes": c.modes, "kind": c.kind, "tier": c.tier, "owner": c.owner,
                               "alert": c.alert, "evidence": reg.evidence.get(c.modes[0], [])[:2] if c.modes else []}
                           for k, c in reg.cards.items()},
                 "tiers": {k: len(v) for k, v in tiers.items()}, "kinds": dict(kinds),
                 "refused": [(a, b, c) for a, b, c in reg.refused]}

# ---- B. the wrong-fee metric on the March draw
head("B. Wrong fee explanation, card v1.0 (draft) on the March fee draw")
mar = MAR.build()
fee_frame = [r for r in mar if r["flow"] == "fee_explanation" and r["status"] != "abandoned"]
abandoned = sum(1 for r in mar if r["flow"] == "fee_explanation" and r["status"] == "abandoned")
draw = random.Random(2026).sample(fee_frame, 200)
draw.sort(key=lambda r: r["trace_id"])
print(f"March frame {len(mar):,} conversations, {mar[0]['trace_id']} to {mar[-1]['trace_id']}; "
      f"fee {len(fee_frame) + abandoned:,} of which abandoned {abandoned} (declared exclusion); draw 200, seed 2026")
out0 = ["deferred" if r["deferred"] else ("fail" if r["wrong_fee"] else "pass") for r in draw]
mc02 = reg.cards["MC-02"]
v10 = M.measure(mc02, out0)
print(f"v1.0 (deferred counts as fail): {pct(v10['fail'], v10['n'])}")
print(f"Chapter 2 pooled: {pct(14, 147)}")
fails = [r for r, o in zip(draw, out0) if o != "pass"]
cat = Counter()
for r in fails:
    if r["wrong_fee"]:
        cat[{"F_waive": "wrong: FM-06 waiver not applied", "X_wrongloan": "wrong: FM-22 other loan's fee",
             "X_invent": "wrong: FM-24 fee stated after tool error"}[r["cause"]]] += 1
    elif r["waive_status"] == "review":
        cat["deferred: waiver under review (tool says review)"] += 1
    elif r.get("tool_error"):
        cat["deferred: fee tool failed, Compass said so"] += 1
    else:
        cat["deferred: tool gave a definite answer"] += 1
for k, v in sorted(cat.items()):
    print(f"  {v:>3}  {k}")
mc02.amend("2027-03-19", "deferral to a loan officer is not a wrong explanation (Victor's ruling, 19 March); "
           "deferral rate reported beside the rate, alert at 15%", deferred_as="pass")
v11 = M.measure(mc02, out0)
print(f"v1.1 (deferred counts as pass): {pct(v11['fail'], v11['n'])}; deferred {v11['deferred']} "
      f"({v11['deferred'] / 200:.1%}); one-sided 95% bound {v11['upper']:.1%}; meets 2% target: {v11['meets_target']}")
excl = M.Card("x", "x", ("FM-06",), "", "", "judge", "inform", "", deferred_as="excluded")
v_ex = M.measure(excl, out0)
print(f"   if deferred were excluded: {pct(v_ex['fail'], v_ex['n'])}")
fee_wrong_frame = sum(r["wrong_fee"] for r in fee_frame)
print(f"fixture truth over the whole fee frame: {pct(fee_wrong_frame, len(fee_frame))}")
print(f"traces needed to show under 2% at 95% with 0 / 1 / 2 failures: "
      f"{traces_needed(.02, 0)} / {traces_needed(.02, 1)} / {traces_needed(.02, 2)}")
fm24_draw = [r["trace_id"] for r in draw if r["cause"] == "X_invent"]
fm22_draw = [r["trace_id"] for r in draw if r["cause"] == "X_wrongloan"]
fm06_draw = [r["trace_id"] for r in draw if r["cause"] == "F_waive"]
defer_def = [r["trace_id"] for r in draw if r["deferred"] and r["waive_status"] != "review" and not r.get("tool_error")]
print("FM-06 ids:", fm06_draw, "\nFM-22 ids:", fm22_draw, "\nFM-24 ids:", fm24_draw, "\nneedless deferral ids:", defer_def)
R["fee"] = {"frame": len(fee_frame), "abandoned": abandoned, "first": mar[0]["trace_id"], "last": mar[-1]["trace_id"],
            "march_total": len(mar), "v10": v10, "v11": v11, "excluded": v_ex, "cats": dict(cat),
            "truth": (fee_wrong_frame, len(fee_frame)), "ids": {"FM-06": fm06_draw, "FM-22": fm22_draw, "FM-24": fm24_draw,
                                                                  "needless": defer_def},
            "need2": [traces_needed(.02, k) for k in (0, 1, 2)]}

# ---- C. scale study: the same 200 under binary, 1-5 and pairwise
head("C. Binary, 1 to 5 and pairwise on the same 200 (simulated readers; assumptions in compass_sim.py)")
prod = {r["trace_id"]: C.reply(r, "production") for r in draw}
cand = {r["trace_id"]: C.reply(r, "rc-0322-1") for r in draw}
ws = [prod[r["trace_id"]]["words"] for r in draw]
mw, sw = st.mean(ws), st.pstdev(ws)
bA = [C.binary(r, "lead", prod[r["trace_id"]]["outcome"]) for r in draw]
bB = [C.binary(r, "Ben", prod[r["trace_id"]]["outcome"]) for r in draw]
lA = [C.likert(r, "lead", prod[r["trace_id"]]["outcome"], prod[r["trace_id"]]["words"], mw, sw) for r in draw]
lB = [C.likert(r, "Ben", prod[r["trace_id"]]["outcome"], prod[r["trace_id"]]["words"], mw, sw) for r in draw]
truth = [prod[r["trace_id"]]["outcome"] for r in draw]
kb = kappa(bA, bB)
agree_b = sum(a == b for a, b in zip(bA, bB)) / 200
print(f"binary: agreement {agree_b:.1%}, kappa {kb:.2f}; fails found lead {bA.count('fail')}, Ben {bB.count('fail')}, "
      f"truth {truth.count('fail')}")
exact = sum(a == b for a, b in zip(lA, lB)) / 200
within1 = sum(abs(a - b) <= 1 for a, b in zip(lA, lB)) / 200
wk = M.weighted_kappa(lA, lB)
print(f"1 to 5: exact agreement {exact:.1%}, within one point {within1:.1%}, quadratic-weighted kappa {wk:.2f}")
dist = {}
for who, L in (("lead", lA), ("Ben", lB)):
    for t in ("pass", "fail", "deferred"):
        dist[f"{who}-{t}"] = [sum(1 for s, o in zip(L, truth) if o == t and s == v) for v in range(1, 6)]
    print(f"  {who:<5} scores of wrong replies {dist[f'{who}-fail']}, of right replies {dist[f'{who}-pass']}, "
          f"of deferrals {dist[f'{who}-deferred']}")
cuts = {}
for who, L in (("lead", lA), ("Ben", lB)):
    for cut in (1, 2, 3):
        k = sum(1 for s in L if s <= cut)
        cuts[f"{who}<={cut}"] = k
    print(f"  {who:<5} 'wrong' if score <= 1: {cuts[f'{who}<=1']}, <= 2: {cuts[f'{who}<=2']}, <= 3: {cuts[f'{who}<=3']}")
right = [(s, prod[r["trace_id"]]["words"]) for s, r, o in zip(lA, draw, truth) if o == "pass"]
from scipy.stats import spearmanr  # noqa: E402
rho = spearmanr([a for a, _ in right], [b for _, b in right]).statistic
print(f"  among right replies, lead's score vs length: Spearman {rho:.2f}")
pA, pB, longer_pref, both_ok, decided = [], [], 0, 0, 0
for r in draw:
    a = (prod[r["trace_id"]]["outcome"], prod[r["trace_id"]]["words"])
    b = (cand[r["trace_id"]]["outcome"], cand[r["trace_id"]]["words"])
    xa, xb = C.pairwise(r, "lead", a, b), C.pairwise(r, "Ben", a, b)
    pA.append(xa); pB.append(xb)
    if (a[0] != "fail") == (b[0] != "fail") and xa != "tie":
        both_ok += 1
        longer_pref += (xa == "A") == (a[1] >= b[1])
agree_p = sum(a == b for a, b in zip(pA, pB)) / 200
print(f"pairwise production (A) vs rc-0322-1 (B): lead prefers B {pA.count('B')}, A {pA.count('A')}, tie {pA.count('tie')}; "
      f"readers agree {agree_p:.1%}, kappa {kappa(pA, pB):.2f}")
print(f"  equally right pairs with a preference: {both_ok}; longer reply preferred {longer_pref} ({longer_pref / both_ok:.1%})")
c_fail = sum(1 for r in draw if cand[r['trace_id']]['outcome'] == 'fail')
print(f"  what pairwise cannot say: production wrong {truth.count('fail')} in 200, candidate wrong {c_fail} in 200")
R["scale"] = {"binary": {"agree": agree_b, "kappa": kb, "lead": bA.count("fail"), "Ben": bB.count("fail"),
                         "truth": truth.count("fail")},
              "likert": {"exact": exact, "within1": within1, "wkappa": wk, "dist": dist, "cuts": cuts, "rho_len": rho},
              "pairwise": {"B": pA.count("B"), "A": pA.count("A"), "tie": pA.count("tie"), "agree": agree_p,
                           "kappa": kappa(pA, pB), "both_ok": both_ok, "longer": longer_pref,
                           "prod_fail": truth.count("fail"), "cand_fail": c_fail},
              "assumptions": {"readers": C.READERS, "polish": C.POLISH, "noise": C.NOISE, "longer": C.LONGER}}

# ---- D. composite
head("D. Composites: the March pass rate by flow, weighted by traffic")
flows = list(FEB.SHARES)
mar_nab = [r for r in mar if r["status"] != "abandoned"]
rate = {}
for f in flows:
    rs = [r for r in mar_nab if r["flow"] == f]
    rate[f] = 1 - sum(1 for r in rs if r["cause"]) / len(rs)
w = dict(FEB.SHARES)
comp, parts = M.composite(rate, w)
need = M.move_needed(w, 0.01)
for f in flows:
    print(f"  {f:<18} share {w[f]:.0%}  pass {rate[f]:.1%}  contributes {parts[f]:.3f}  "
          f"pass-rate change that alone moves the score 0.01: {need[f]:.1%}")
print(f"Compass score (traffic-weighted pass rate): {comp:.3f}")
hard = [r for r in mar_nab if r["flow"] == "hardship"]
hf = 1 - rate["hardship"]
wrong_off = sum(1 for r in hard if r["offered_loan_recent_deferral"])
offers = sum(1 for r in hard if r["offer_drafted"])
print(f"hardship: {len(hard)} conversations, {offers} offers drafted, wrong offers (fixture truth) {wrong_off}")
r2 = dict(rate); r2["hardship"] = 1 - 2 * hf
c2, _ = M.composite(r2, w)
st_ = [r for r in mar_nab if r["flow"] == "statement_request"]
ye = sum(1 for r in st_ if r["cause"] == "S_yearend") / len(st_)
ref = sum(1 for r in hard if r["cause"] == "H_refused") / len(hard)
r3 = dict(rate); r3["statement_request"] = rate["statement_request"] + ye; r3["hardship"] = rate["hardship"] - ref
c3, _ = M.composite(r3, w)
w4 = dict(w); w4.update(hardship=.12, account_question=.33)
c4, _ = M.composite(rate, w4)
print(f"scenario: every hardship failure doubles -> score {c2:.3f} (moves {c2 - comp:+.3f})")
print(f"scenario: FM-18 fixed ({ye:.1%} of statements) while FM-20 doubles ({ref:.1%} more of hardship) -> {c3:.3f} ({c3 - comp:+.3f})")
print(f"scenario: hardship share doubles to 12% (account 33%), no rate changes -> {c4:.3f} ({c4 - comp:+.3f})")
R["composite"] = {"rate": rate, "w": w, "score": comp, "parts": parts, "need": need, "double_hardship": c2,
                  "trade": c3, "ye": ye, "ref": ref, "mix": c4, "w4": w4, "hard_n": len(hard), "offers": offers,
                  "wrong_offers": wrong_off}

# ---- E. monitor alerts: reset on 26 March so a quiet four weeks alerts at most 5% of the time
head("E. Monitor alerts, reset 26 March 2027 for a four-week pooled draw of 200 (exact binomial; alerts.py)")
import alerts as AL  # noqa: E402
mar_live = [r for r in mar if r["status"] != "abandoned"]
R["alerts"] = {}
for cid, c in reg.cards.items():
    if c.tier != "monitor":
        continue
    p, week = AL.mode_rate(mar_live, c)
    old_alert, new_alert = c.alert, AL.best_alert(200, p)
    c.amend("2027-03-26", f"alert reset from {old_alert:.0%} to {new_alert:.1%} of a four-week pooled draw of 200 "
            "(quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands", alert=round(new_alert, 3))
    R["alerts"][cid] = {"rate": p, "old": old_alert, "new": new_alert, "false_old_50": AL.tail(50, p, old_alert),
                        "catch_new_200": AL.tail(200, min(1, 2 * p), new_alert)}
    print(f"  {cid} {c.modes[0]} rate {p:.1%}: weekly 50 at {old_alert:.0%} alerts {AL.tail(50, p, old_alert):.0%} of quiet weeks;"
          f" new alert {new_alert:.1%} on 200 pooled catches a doubling {AL.tail(200, min(1, 2 * p), new_alert):.0%}")

# ---- F. cards (written out; the chapter prints MC-02)
cards_md = ["# Compass metric cards, Truss v1 (0.11.0), taxonomy v0.3 (" + SU.TAX["digest"] + ")", ""]
for cid, c in reg.cards.items():
    cards_md += [M.to_markdown(c, v11 if cid == "MC-02" else None), ""]
(OUT / "metric-cards.md").write_text("\n".join(cards_md))

# ---- G. the fee replay set and the first before/after tables
head("G. Fee replay set: the 70 frozen fee cases and the 200 March fee draw")
pilot = MAR.pilot_fee_cases(SU.pilot_fee_ids())
replay = pilot + draw
print(f"replay set {len(replay)} ({len(pilot)} frozen + {len(draw)} March); manifest fee-replay-2027-03")
ba = {}
fee_cards = [reg.cards[k] for k in ("MC-02", "MC-06", "MC-19", "MC-21")]
mode_of = {"MC-06": "F_waive", "MC-19": "X_wrongloan", "MC-21": "X_invent"}


def outcomes(rel):
    rep = {r["trace_id"]: C.reply(r, rel) for r in replay}
    o = {"MC-02": {t: x["outcome"] for t, x in rep.items()}}
    for cid, cause in mode_of.items():
        o[cid] = {t: ("fail" if x["cause"] == cause else "pass") for t, x in rep.items()}
    return o, rep


base, brep = outcomes("production")
for rel in ("rc-0322-1", "rc-0326-2"):
    cand_o, crep = outcomes(rel)
    rows, decision, holds = M.before_after(fee_cards, base, cand_o)
    print(f"\n{rel}: decision {decision.upper()}  {holds}")
    for x in rows:
        lo, hi = x["after_wilson"]
        print(f"  {x['card']} {x['name'][:44]:<44} {x['before'][0]:>3}/{x['before'][1]}  ->  {x['after'][0]:>3}/{x['after'][1]}"
              f"  (after {x['after_rate']:.1%}, {lo:.1%} to {hi:.1%})  newly fail {len(x['newly_fail'])}  newly pass {len(x['newly_pass'])}"
              f"  {x['verdict']}")
    sig = {}
    for nm, rep in (("before", brep), ("after", crep)):
        wd = [x["words"] for x in rep.values()]
        tm = [x["terms"] / 8 for x in rep.values()]
        sig[nm] = {"words": st.mean(wd), "completeness": st.mean(tm),
                   "deferred": sum(x["outcome"] == "deferred" for x in rep.values())}
    print(f"  signals: mean words {sig['before']['words']:.0f} -> {sig['after']['words']:.0f}; vendor completeness "
          f"{sig['before']['completeness']:.2f} -> {sig['after']['completeness']:.2f}; deferred "
          f"{sig['before']['deferred']} -> {sig['after']['deferred']}")
    vq0 = 0.5 * sig["before"]["completeness"] + 0.5 * (1 - rows[0]["before_rate"])
    vq1 = 0.5 * sig["after"]["completeness"] + 0.5 * (1 - rows[0]["after_rate"])
    print(f"  vendor fee quality index (0.5 completeness + 0.5 pass): {vq0:.3f} -> {vq1:.3f}")
    checks = {"FM-22 census check": sum(x["cause"] == "X_wrongloan" for x in crep.values()),
              "FM-24 census check": sum(x["cause"] == "X_invent" for x in crep.values())}
    newly = rows[0]["newly_fail"]
    print(f"  L1 checks on candidate replays: {checks}; MC-02 newly failing: {newly}")
    ba[rel] = {"rows": rows, "decision": decision, "holds": holds, "signals": sig, "vendor": (vq0, vq1),
               "checks": checks, "newly": newly}
R["replay"] = {"n": len(replay), "pilot": len(pilot), "march": len(draw), "ba": ba}

# ---- H. hours (rates from the ledger: lead and Ryan $85/h, loan officers $60/h)
head("H. Hours")
plan = [("first reading, March fee draw (200 x 2.0 min)", "lead", 200 * 2.0 / 60, 85),
        ("dispute reading, 38 non-passing traces with Ryan (x 4 min each)", "lead", 38 * 4 / 60, 85),
        ("dispute reading (Ryan)", "Ryan", 38 * 4 / 60, 85),
        ("scale study, lead: binary 1.2 + 1-5 1.3 + pairwise 2.2 min x 200", "lead", 200 * 4.7 / 60, 85),
        ("scale study, Ben Fletcher (same)", "Ben", 200 * 4.7 / 60, 60),
        ("metric cards, 21 (20 min each)", "lead", 21 * 20 / 60, 85),
        ("gate reading of newly failing traces, two runs", "lead", 1.0, 85)]
tot_h = sum(h for _, _, h, _ in plan)
tot_d = sum(h * r for _, _, h, r in plan)
for a, p, h, r in plan:
    print(f"  {a:<75} {p:<5} {h:5.1f} h  ${h * r:,.0f}")
print(f"  total {tot_h:.1f} h, ${tot_d:,.0f}")
R["hours"] = {"rows": [(a, p, h, h * r) for a, p, h, r in plan], "total": tot_h, "dollars": tot_d}

json.dump(R, open(OUT / "lab.json", "w"), indent=1, default=str)
print("\nwrote out/lab.json, out/metric-cards.md")
