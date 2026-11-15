"""Chapter 15 lab: the metric suite for the hardship flow, built in one workshop (13 to 24 September 2027).

A  the flow: the September frame and where each step can go wrong
B  its taxonomy: production replay on hardship gold, failures by direction, segment and mode
C  code checks: census over every September hardship conversation; C-03 under two readings
D  the golden set: composition against September traffic (truss.flowsuite.composition_audit)
E  the two metrics that gate: the decision table, then the two-direction gate on the REAL probe
F  what Victor asked: the rate, its interval, and whether any sample size can answer him
Gold labels, Compass replays, spans and officers are SIMULATED (fixture.py); the probe is REAL (probe.py).
Run: python3 lab.py   (writes out/lab.json)"""
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
import fixture as FX  # noqa: E402
import probe as PR  # noqa: E402
from truss import __version__  # noqa: E402
from truss import flowsuite as FS  # noqa: E402
from truss.checks import Verifier, Suite, Result, PASS, FAIL, NA, CANNOT, tally, months_before, within_months, precision_recall  # noqa: E402
from truss.rates import wilson, upper_bound, traces_needed  # noqa: E402

OUT = HERE / "out"
R = {"truss": __version__}
OFFER = FX.OFFER


def head(s):
    print(f"\n== {s}")


def pct(k, n):
    return f"{k}/{n} ({k / n:.1%})" if n else f"{k}/0"


G = FX.gold()
F = FX.frame()

# ---- A
head("A. The flow: every hardship conversation, Mon 6 to Sun 19 September 2027 (SIMULATED)")
req = Counter(FX.required(f) for f in F)
prod = Counter(f["prod"] for f in F)
print(f"  {len(F)} conversations, {F[0]['trace_id']} to {F[-1]['trace_id']}; required first action {dict(req)}")
print(f"  production build's action {dict(prod)}")
steps = [("1 intent", "router labels hardship", "FM-21 (bereavement routed as hardship)"),
         ("2 account lookup", "servicing core: loans, arrears, employment on file, relief history", "FM-22, FM-24"),
         ("3 which loan", "4.6", "FM-08, FM-22"), ("4 income", "4.2", "FM-01"),
         ("5 window", "4.3 with HB-2027-07", "FM-04 (offer inside), FM-20 (refusal outside)"),
         ("6 referral", "4.5 (self-employed, three or more behind)", "no mode yet (see B)"),
         ("7 draft", "deferral drafted for officer approval", "FM-03 (approval sentence missing)"),
         ("8 hand-off", "officer callback or queue", "FM-14, FM-15, FM-16")]
for s in steps:
    print(f"  {s[0]:18s} {s[1]:64s} {s[2]}")
offers = [f for f in F if f["prod"] == OFFER]
print(f"  offers drafted {len(offers)} ({len(offers) / len(F):.1%} of conversations); "
      f"documented income {sum(f['documented'] for f in F)}; tool errors {sum(f['tool_error'] for f in F)}")
R["A"] = {"n": len(F), "first": F[0]["trace_id"], "last": F[-1]["trace_id"], "required": dict(req), "prod": dict(prod),
          "offers": len(offers), "documented": sum(f["documented"] for f in F), "tool_errors": sum(f["tool_error"] for f in F)}

# ---- B
head(f"B. Its taxonomy: the production build replayed on hardship gold ({len(G)} labels; SIMULATED replay)")
print(f"  gold {len(G)}: {dict(Counter(c['source'] for c in G))}")
wo = [c for c in G if c["prod"] == OFFER and c["gold"] != OFFER]
elig = [c for c in G if c["gold"] == OFFER]
wr = [c for c in G if c["prod"] != OFFER and c["gold"] == OFFER]
other = [c for c in G if c["prod"] != c["gold"] and c not in wo and c not in wr]
drafted = [c for c in G if c["prod"] == OFFER]   # MC-01's population (Chapter 8): conversations with an offer drafted
lo, hi = wilson(len(wo), len(drafted))
print(f"  offers drafted on replay {len(drafted)} of {len(G)} gold conversations")
print(f"  MC-01 wrong offers {pct(len(wo), len(drafted))} of offers drafted, Wilson {lo:.2%} to {hi:.2%}, "
      f"one-sided bound {upper_bound(len(wo), len(drafted)):.2%}  (per gold conversation {len(wo) / len(G):.2%})")
print(f"  wrong offers by source {dict(Counter(c['source'] for c in wo))}")
lo2, hi2 = wilson(len(wr), len(elig))
print(f"  eligible borrowers not offered {pct(len(wr), len(elig))}, Wilson {lo2:.1%} to {hi2:.1%}")
print(f"  other wrong first actions (neither direction of the offer) {len(other)}: {dict(Counter((c['gold'], c['prod']) for c in other))}")
MODE = {"decline_window": "FM-04", "ask_income": "FM-01", "ask_which_loan": "FM-08",
        "refer_to_officer": "none (4.5 referral skipped)"}


def code_of(c, direction):
    """Wrong offers are coded by what gold required; refusals by what Compass did instead."""
    if direction == "offer":
        return MODE[c["gold"]]
    return "FM-20" if c["prod"] == "decline_window" else "none"


rows = [(c["segment"], "offer", code_of(c, "offer"), c["prod"], c["gold"]) for c in wo] + \
       [(c["segment"], "refusal", code_of(c, "refusal"), c["prod"], c["gold"]) for c in wr]
for r in sorted(rows):
    print(f"    {r[1]:8s} {r[0]:24s} {r[2]:28s} Compass {r[3]:17s} gold {r[4]}")
modes = Counter(r[2] for r in rows)
print(f"  by mode {dict(modes)}; uncoded {sum(v for k, v in modes.items() if k.startswith('none'))} of {len(rows)}")
R["B"] = {"gold": len(G), "sources": dict(Counter(c["source"] for c in G)), "wrong_offers": len(wo), "drafted": len(drafted),
          "wo_wilson": (lo, hi), "wo_upper": upper_bound(len(wo), len(drafted)), "eligible": len(elig), "refusals": len(wr),
          "wr_wilson": (lo2, hi2), "other": len(other), "rows": rows, "modes": dict(modes),
          "wo_by_seg": dict(Counter(c["segment"] for c in wo)), "wr_by_seg": dict(Counter(c["segment"] for c in wr)),
          "wr_by_action": dict(Counter(c["prod"] for c in wr)),
          "seg_n": dict(Counter(c["segment"] for c in G))}

# ---- C
head("C. Code checks: census over the September frame (480 conversations; spans SIMULATED)")


def conv_date(t):
    return date.fromisoformat(t["date"])


def end_date(t):
    return months_before(conv_date(t), t["relief"]["end_months_ago"])


def c01(t, up):
    if not t["tool_error"]:
        return Result(NA, "no tool error", "C-01")
    return Result(FAIL if t["answered_through_error"] else PASS, "reply after a failed tool call", "C-01")


def c02(t, up):
    if t["loans"] == 1 or not t["names_loan"]:
        return Result(NA, "one loan or none named", "C-02")
    return Result(FAIL if t["wrong_loan_tool"] else PASS, "tool loan against loan named", "C-02")


def make_c03(anniversary_inside):
    def c03(t, up):
        rel = t["relief"]
        if t["prod"] not in (OFFER, "decline_window"):
            return Result(NA, "no window decision", "C-03")
        if rel is None or rel["kind"] == "disaster":
            return Result(FAIL if t["prod"] == "decline_window" else PASS, "no countable relief", "C-03",
                          {"direction": "offer" if t["prod"] == OFFER else "refusal"})
        inside = within_months(end_date(t), conv_date(t), 12, anniversary_inside=anniversary_inside)
        bad = (t["prod"] == OFFER and inside) or (t["prod"] == "decline_window" and not inside)
        return Result(FAIL if bad else PASS, f"relief ended {end_date(t)}; inside {inside}", "C-03",
                      {"direction": "offer" if t["prod"] == OFFER else "refusal"})
    return c03


def c04(t, up):
    if t["prod"] != OFFER:
        return Result(NA, "no offer", "C-04")
    return Result(PASS if t["approval_sentence"] else FAIL, "approval sentence", "C-04")


def c09(t, up):
    if t["prod"] != OFFER:
        return Result(NA, "no offer", "C-09")
    return Result(FAIL if (t["self_employed"] or t["behind"] >= 3) else PASS, "4.5 from the record", "C-09")


def suite(anniv_inside):
    return Suite([Verifier("C-01", "tool returns", c01, ("FM-24",)), Verifier("C-02", "loan named", c02, ("FM-22",)),
                  Verifier("C-03", "deferral window", make_c03(anniv_inside), ("FM-04", "FM-20"), needs=("C-01",)),
                  Verifier("C-04", "approval disclosure", c04, ("FM-03",)),
                  Verifier("C-09", "referral from the record", c09, ())])


out_old, secs = suite(True).run_all(F)
out_new, _ = suite(False).run_all(F)
truth_wo = {f["trace_id"] for f in F if f["prod"] == OFFER and FX.required(f) != OFFER}
truth_wr = {f["trace_id"] for f in F if f["prod"] != OFFER and FX.required(f) == OFFER}
cen = {}
for vid in ("C-01", "C-02", "C-03", "C-04", "C-09"):
    a, b = tally(out_old, vid), tally(out_new, vid)
    cen[vid] = {"v1.0": a, "v1.1": b}
    print(f"  {vid}: v1.0 (anniversary inside) {a}   v1.1 (anniversary outside) {b}")
print(f"  {len(F)} conversations checked in {secs * 1000:.0f} ms")
anniv = [f for f in F if f["segment"] == "anniversary"]
anniv_dec = [f for f in anniv if f["prod"] == "decline_window"]
old_pass_dec = sum(out_old[f["trace_id"]]["C-03"].outcome == PASS for f in anniv_dec)
new_fail_dec = sum(out_new[f["trace_id"]]["C-03"].outcome == FAIL for f in anniv_dec)
print(f"  anniversary conversations {len(anniv)}; production declined {len(anniv_dec)}; C-03 v1.0 passes {old_pass_dec} of those, "
      f"v1.1 fails {new_fail_dec}")
only_old = [f for f in F if out_old[f["trace_id"]]["C-03"].outcome == FAIL and out_new[f["trace_id"]]["C-03"].outcome != FAIL]
only_new = [f for f in F if out_new[f["trace_id"]]["C-03"].outcome == FAIL and out_old[f["trace_id"]]["C-03"].outcome != FAIL]
print(f"  C-03 fails under v1.0 only: {len(only_old)} {dict(Counter((f['segment'], f['prod']) for f in only_old))}; "
      f"under v1.1 only: {len(only_new)} {dict(Counter((f['segment'], f['prod']) for f in only_new))}")
flag_wo = {t for t, r in out_new.items() if (r["C-03"].outcome == FAIL and r["C-03"].data.get("direction") == "offer")
           or r["C-09"].outcome == FAIL}
flag_wr = {t for t, r in out_new.items() if r["C-03"].outcome == FAIL and r["C-03"].data.get("direction") == "refusal"}
pr_wo = precision_recall(flag_wo, {f["trace_id"] for f in F}, truth_wo)
pr_wr = precision_recall(flag_wr, {f["trace_id"] for f in F}, truth_wr)
print(f"  wrong offers in the frame (fixture truth) {len(truth_wo)}; flagged by C-03 or C-09 {len(flag_wo)}; "
      f"precision {pr_wo['precision']}, recall {pr_wo['recall']}; missed {pr_wo['missed_in_sample']}")
missed = [f for f in F if f["trace_id"] in pr_wo["missed_in_sample"]]
print(f"    missed by code, by segment: {dict(Counter(f['segment'] for f in missed))}")
ff = [f for f in F if f["trace_id"] in pr_wr["false_flags"]]
print(f"  C-03 refusal flags that are not wrongful refusals: {len(ff)}, required {dict(Counter(FX.required(f) for f in ff))}")
print(f"  wrongful refusals in the frame (fixture truth) {len(truth_wr)}; flagged by C-03 v1.1 {len(flag_wr)}; "
      f"precision {pr_wr['precision']}, recall {pr_wr['recall']}")
missed_r = [f for f in F if f["trace_id"] in pr_wr["missed_in_sample"]]
print(f"    missed by code: {dict(Counter((f['segment'], f['prod']) for f in missed_r))}")
# validation against the 60 gold labels from the week of 6 September (what the team can actually compute)
wk = [c for c in G if c["source"] == "week of 6 September"]
wk_ids = {c["trace_id"] for c in wk}
gold_wo = {c["trace_id"] for c in wk if c["prod"] == OFFER and c["gold"] != OFFER}
gold_wr = {c["trace_id"] for c in wk if c["prod"] != OFFER and c["gold"] == OFFER}
print(f"  against the 60 gold labels from the week of 6 September: gold wrong offers {len(gold_wo)}, flagged {len(flag_wo & wk_ids)}; "
      f"gold wrongful refusals {len(gold_wr)}, flagged {len(flag_wr & wk_ids)}")
R["C"] = {"census": cen, "ms": secs * 1000, "anniv": len(anniv), "anniv_declined": len(anniv_dec), "c03_only_old": len(only_old), "c03_only_new": len(only_new), "old_pass": old_pass_dec,
          "new_fail": new_fail_dec, "truth_wo": len(truth_wo), "flag_wo": len(flag_wo), "pr_wo": [pr_wo["precision"], pr_wo["recall"]],
          "missed_wo": dict(Counter(f["segment"] for f in missed)), "truth_wr": len(truth_wr), "flag_wr": len(flag_wr),
          "pr_wr": [pr_wr["precision"], pr_wr["recall"]], "missed_wr": {f"{a}|{b}": n for (a, b), n in Counter((f['segment'], f['prod']) for f in missed_r).items()},
          "wk_gold_wo": len(gold_wo), "wk_flag_wo": len(flag_wo & wk_ids), "wk_gold_wr": len(gold_wr), "wk_flag_wr": len(flag_wr & wk_ids)}

# ---- D
head("D. The golden set against September traffic (truss.flowsuite.composition_audit, min 20 cases, share at least half of traffic)")
aud = FS.composition_audit(G, F, FX.flags, min_n=20, min_ratio=0.5)
for s, r in aud["segments"].items():
    ub = upper_bound(0, r["gate_n"]) if r["gate_n"] else 1.0
    print(f"  {s:26s} gold {r['gate_n']:4d} ({r['gate_share']:5.1%})  traffic {r['frame_n']:3d} ({r['frame_share']:5.1%})  "
          f"{'ok  ' if r['pass'] else 'FAIL'} {r['why']:40s} bound at zero failures {ub:.1%}")
print(f"  verdict {aud['verdict']}; failing {aud['failing']}")
old = [c for c in G if c["source"].startswith("hardship-gold v1.0")]
print(f"  anniversary and stated-work cases among the 299 Chapter 13 labels: "
      f"{sum(c['segment'] in ('anniversary', 'stated change of work') for c in old)}")
R["D"] = aud

# ---- E
head("E. The two metrics that gate")
table = [
    FS.Row("MC-01", "offer drafted where policy requires another first action", "any stable new failure on replay; rate reported to Victor with its bound",
           "Grace Holloway", "hold the release; Grace reads every new failure", "gate"),
    FS.Row("MC-17", "eligible borrower not offered (any other first action)", "any stable new failure on replay",
           "Grace Holloway", "hold the release; Grace reads every new failure", "gate"),
    FS.Row("C-01..C-04", "layer-one checks on every hardship replay case", "any failure", "Ryan Mitchell", "block the build", "gate"),
    FS.Row("MC-03", "offer drafted before income (FM-01)", "weekly rate above 1%", "Grace Holloway", "read the week's offers", "monitor"),
    FS.Row("MC-11", "request for a person ignored (FM-14)", "weekly count above 3", "Grace Holloway", "read and route", "monitor"),
    FS.Row("MC-13", "Spanish hand-off not recognised (FM-16)", "any in a week", "Ryan Mitchell", "fix the router tag", "monitor"),
    FS.Row("MC-18", "bereavement treated as ordinary hardship (FM-21)", "any in a week", "Grace Holloway", "call the borrower within a day", "monitor"),
    FS.Row("S-02", "self-serve rate on hardship (context only)", "", "Rachel Foster", "", "inform"),
    FS.Row("decision accuracy", "share of first actions matching gold", "", "", "", "monitor"),
    FS.Row("offer rate", "share of hardship conversations with an offer drafted", "", "Rachel Foster", "", "monitor"),
]
dt = FS.decision_table(table)
for r in dt["kept"]:
    print(f"  keep {r.tier:7s} {r.metric:18s} {r.threshold:62s} {r.owner}")
for r, why in dt["dropped"]:
    print(f"  drop         {r.metric:18s} {why}")
R["E_table"] = {"kept": [r.__dict__ for r in dt["kept"]], "dropped": [(r.__dict__, w) for r, w in dt["dropped"]]}

C = PR.cached()
cs = {c["id"]: c for c in PR.cases()}
required = {i: c["required"] for i, c in cs.items()}
runs = {pv: [{i: PR.action(C[(i, pv, rep)]["raw"]) for i in cs} for rep in (1, 2)] for pv in PR.PROMPTS}
R["E_gate"] = {}
print(f"  REAL probe ({PR.MODEL}, 160 authored cases, two runs each; {len(C)} calls cached)")
for pv in ("rc-0913-1", "rc-0915-2", "rc-0917-3"):
    g = FS.two_way_gate(required, runs["hardship-prompt-p7"], runs[pv])
    R["E_gate"][pv] = g
    print(f"  {pv}: accuracy {g['accuracy']['base']} -> {g['accuracy']['cand']} of 160; "
          f"wrong offers {g['offer']['base']} -> {g['offer']['cand']}, stable new {len(g['offer']['new'])}, one run only {len(g['offer']['single_run'])}; "
          f"refusals {g['refusal']['base']} -> {g['refusal']['cand']} of {g['refusal']['n']}, stable new {len(g['refusal']['new'])}; "
          f"verdict {g['verdict'].upper()} {g['holds_on']}")
    if g["offer"]["single_run"]:
        print(f"    one-run-only new wrong offers {g['offer']['single_run']}; production's own flips between runs "
              f"{len(g['offer']['production_flips'])} {g['offer']['production_flips']}")
acc_only = {pv: ("ship" if sum(R['E_gate'][pv]['accuracy']['cand']) > sum(R['E_gate'][pv]['accuracy']['base']) else "hold")
            for pv in R["E_gate"]}
print(f"  an accuracy-only gate (ship if correct first actions rise over both runs): {acc_only}")
R["E_acc_only"] = acc_only

# ---- F
head("F. What Victor asked: is the wrong-offer rate under 0.5%?")
rc = FS.reachable(len(wo), len(drafted), 0.005)
gold_wk = 60 * len(drafted) / len(G)          # offers a week of 60 gold labels adds
census_wk = len(offers) / 2                    # offers drafted a week in live traffic (frame is two weeks)
print(f"  observed {len(wo)}/{len(drafted)} offers = {rc['rate']:.2%}; Wilson {rc['wilson'][0]:.2%} to {rc['wilson'][1]:.2%}; "
      f"one-sided 95% bound {rc['upper']:.2%}; target 0.50%")
print(f"  reachable by sampling alone: {rc['reachable_by_sampling']} (the observed rate is above the target)")
print(f"  offers needed for a bound under 0.5% at 0, 1, 2, 3 wrong: {[traces_needed(0.005, k) for k in range(4)]}")
print(f"  offers a week: {gold_wk:.1f} from 60 gold labels; {census_wk:.1f} in live traffic (census)")
need = {}
for true in (0.001, 0.002, 0.003, 0.004, round(len(wo) / len(drafted), 4)):
    n = FS.refine(true, 0.005)
    need[true] = n
    wk_g = FS.weeks_to(n, len(drafted), gold_wk) if n else None
    wk_c = FS.weeks_to(n, 0, census_wk) if n else None
    need[true] = (n, wk_g, wk_c)
    print(f"  if the true rate were {true:.2%}: about {n if n else 'no'} offers"
          + (f"; {wk_g:.0f} more weeks of gold at 60 labels a week, {wk_c:.0f} weeks of census" if n else "; no sample size is enough"))
p0 = (1 - len(wo) / len(drafted)) ** len(drafted)
print(f"  odds a set of {len(drafted)} offers shows 0 wrong if the true rate is {len(wo) / len(drafted):.2%}: {p0:.4f}")
R["F"] = {"rc": rc, "needed": [traces_needed(0.005, k) for k in range(4)], "need_at": {str(k): v for k, v in need.items()},
          "p_zero": p0, "gold_wk": gold_wk, "census_wk": census_wk, "drafted": len(drafted)}

OUT.mkdir(exist_ok=True)
(OUT / "lab.json").write_text(json.dumps(R, indent=1, default=str))
print("\nwrote out/lab.json")
