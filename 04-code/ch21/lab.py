"""Chapter 21 lab: a judge fails its trial. SIMULATED verdicts and gold (fixture.py, seed 2026);
every rate, interval, bound and verdict below is computed by Truss 0.24 `trial` and Truss 0.19 `judge`."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "truss"))
from truss import __version__
from truss.judge import JudgeSpec, admit, guard, Leak, rates, confusion
from truss.drift import version_record
from truss.trial import (validation_table, disagreement_causes, construct_profile, surface_agreement,
                         escape_bound, seen_through, decision_record)
import fixture as fx

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)


def line(t=""):
    print(t)


def pct(x):
    return f"{100 * x:.1f}%"


def ci(c):
    return f"{c[0]:.3f} to {c[1]:.3f}"


dev, test = fx.build()
line("=" * 100)
line(f"Chapter 21 lab: hardship-judge-v1 on trial (Truss {__version__}; SIMULATED verdicts, seed {fx.SEED})")
line("=" * 100)

SPEC = JudgeSpec(
    card="MC-01", card_version="1.0",
    question=("Was the drafted offer one the hardship policy permits for this borrower, given everything "
              "the borrower said and everything on the account record?"),
    rules=["income: take-home pay the borrower states is stated income (HP 4.2)",
           "window: prior relief ending inside twelve calendar months bars a new deferral; the "
           "anniversary day is outside (HP 4.3, C-03 v1.1); a disaster forbearance is not prior relief (HB-2027-07)",
           "referral: self-employed, stated or on record, or three or more payments behind goes to an officer (HP 4.5)",
           "loan: the offer is on the loan the borrower named (HP 4.6)",
           "stated change: a stated change of work outranks the record until an officer confirms it (FM-26)"],
    inputs=("conversation", "account_record", "relief_history", "draft_offer"),
    model="larger model, same family as fee-judge-v1 (stand-in)", version="v1")
rec = version_record("hardship-judge-v1", prompt=SPEC.question + "|".join(SPEC.rules),
                     model_pin="large-2027-09 (stand-in)", rubric="|".join(SPEC.rules),
                     policy_doc="HP-2027-04 + HB-2027-07", card="MC-01 (per drafted offer)", role="order",
                     admitted_on=None)
line(f"Judge: hardship-judge-v1  card MC-01 per drafted offer  digest {rec['digest']}  inputs {', '.join(SPEC.inputs)}")
line(f"Development set {len(dev)} (rules written from these), held-out trial set {len(test)}")
src = {}
for r in test:
    src.setdefault(r["source"], [0, 0])
    src[r["source"]][0] += 1
    src[r["source"]][1] += r["gold"] == "fail"
line("Trial sources (traces, gold wrong offers): " +
     ", ".join(f"{k} {v[0]} ({v[1]})" for k, v in src.items()))

# ---------------------------------------------------------------- development, then the trial
line()
line("-" * 100)
line("1. Development (100) and the held-out trial (200)")
line("-" * 100)
dv = validation_table([r["gold"] for r in dev], [r["v1"] for r in dev], [r["kind"] for r in dev])
tv = validation_table([r["gold"] for r in test], [r["v1"] for r in test], [r["kind"] for r in test],
                      [r["lang"] for r in test])
for name, t in (("development", dv), ("held-out", tv)):
    line(f"{name:12s} n={t['n']:3d}  TP {t['tp']:2d} FN {t['fn']:2d} FP {t['fp']:2d} TN {t['tn']:3d} "
         f"abstain {t['abstain_pos']}+{t['abstain_neg']}  TPR {t['tp']}/{t['P']} = {t['tpr']:.3f} ({ci(t['tpr_ci'])})  "
         f"TNR {t['tn']}/{t['N']} = {t['tnr']:.3f} ({ci(t['tnr_ci'])})  agreement {t['agree_n']}/{t['n']} = "
         f"{pct(t['agreement'])}  kappa {t['kappa']:.3f}")
cm = confusion([r["gold"] for r in test], [r["v1"] for r in test])
adm_dev = admit(SPEC, rates(confusion([r["gold"] for r in dev], [r["v1"] for r in dev])), role="order",
                tested_on_test=True)
adm = admit(SPEC, rates(cm), role="order")
line(f"admit on development (not evidence, shown for contrast): {adm_dev['admit']} {adm_dev['reasons']}")
line(f"admit on held-out, role order: {adm['admit']}  role {adm['role']}  reasons {adm['reasons']}")
line()
line("Validation table by gold kind (held-out):")
line(f"  {'kind':22s} {'n':>4s} {'gold wrong':>10s} {'judge right':>11s} {'abstain':>7s}")
for k in fx.POS_KINDS + fx.NEG_KINDS:
    v = tv["by_kind"][k]
    line(f"  {k:22s} {v['n']:4d} {v['gold_fail']:10d} {v['right']:11d} {v.get('abstain', 0):7d}")
line("By language (held-out):")
for s, v in tv["by_segment"].items():
    line(f"  {s}: n={v['n']}  TPR {v['tp']}/{v['P']} = {v['tpr']:.3f}  TNR {v['tn']}/{v['N']} = {v['tnr']:.3f}")

# ---------------------------------------------------------------- why it failed
line()
line("-" * 100)
line("2. Why it failed: the 31 traces where judge and gold differ, by cause")
line("-" * 100)
dis = [r for r in test if r["v1"] != r["gold"]]
dc = disagreement_causes(dis)
for k, v in dc["by_cause"].items():
    misses = sum(1 for r in dis if r["cause"] == k and r["gold"] == "fail")
    line(f"  {k:18s} {v:3d}   (misses {misses}, false alarms or abstentions {v - misses})")
line(f"  mechanical (arithmetic code already does): {dc['mechanical']}/{dc['n']} = {pct(dc['mechanical_share'])}")
ex = [r["id"] for r in dis if r["kind"] == "window" and r["source"] == "random"]
line(f"  the random production wrong offer the judge passed: {ex[0]} (window, relief ended inside twelve months)")

line()
line("Surface check: a one-feature rule, 'fail if the conversation runs over 15 turns'")
sa = surface_agreement([r["long"] for r in test], [r["v1"] for r in test], [r["gold"] for r in test])
line(f"  reproduces the judge on {sa['judge_k']}/{sa['n']} = {pct(sa['judge'])}; the gold on "
     f"{sa['gold_k']}/{sa['n']} = {pct(sa['gold'])}; gap {100 * sa['gap']:.1f} points")
caught = [r for r in test if r["gold"] == "fail" and r["v1"] == "fail"]
missed = [r for r in test if r["gold"] == "fail" and r["v1"] != "fail"]
line(f"  wrong offers caught that were long: {sum(r['long'] for r in caught)}/{len(caught)}; "
     f"wrong offers missed that were short: {sum(not r['long'] for r in missed)}/{len(missed)}")

line()
line("Construct-validity profile on 40 permitted offers the judge passed (edits planted)")
base, pres, types, ch_v1, ch_jb = fx.construct_edits()
cp = construct_profile(base, pres, ch_v1, types)
line(f"  invariance S = {cp['S_k']}/{cp['S_n']} = {cp['S']:.3f} ({ci(cp['S_ci'])})")
line(f"  sensitivity R = {cp['R_k']}/{cp['R_n']} = {cp['R']:.3f} ({ci(cp['R_ci'])})")
for t, v in cp["R_by_type"].items():
    line(f"    {t:8s} changed {v['changed']}/{v['n']}")

# ---------------------------------------------------------------- can it gate MC-01 at all
line()
line("-" * 100)
line("3. Could any version of this trial let a judge gate the 0.5% target?")
line("-" * 100)
miss_all = sum(1 for r in test if r["gold"] == "fail" and r["v1"] != "fail")
eb = escape_bound(miss_all, len(test))
rnd = [r for r in test if r["source"] == "random"]
miss_rnd = sum(1 for r in rnd if r["gold"] == "fail" and r["v1"] != "fail")
ebr = escape_bound(miss_rnd, len(rnd))
line(f"  wrong offers passed, all 200:      {eb['missed']}/{eb['n']} = {pct(eb['rate'])}, one-sided 95% bound {pct(eb['upper'])}, can gate {eb['can_gate']}")
line(f"  wrong offers passed, random 120:   {ebr['missed']}/{ebr['n']} = {pct(ebr['rate'])}, one-sided 95% bound {pct(ebr['upper'])}, can gate {ebr['can_gate']}")
line(f"  a perfect judge on 200 offers:     0/200, bound {pct(eb['perfect_upper'])}; offers needed at zero misses: {eb['offers_needed_at_zero']}")
line(f"  a candidate whose true rate is 0.8% read through TPR {tv['tpr']:.3f}: {100 * seen_through(0.008, tv['tpr']):.2f}%")

# ---------------------------------------------------------------- option one: fix
line()
line("-" * 100)
line("4. Option one, fix: hardship-judge-v2 (C-03 result and a days calculator as inputs, two new rules)")
line("-" * 100)
v2 = validation_table([r["gold"] for r in test], [r["v2"] for r in test], [r["kind"] for r in test])
line(f"  on the same 200: TPR {v2['tp']}/{v2['P']} = {v2['tpr']:.3f} ({ci(v2['tpr_ci'])})  "
     f"TNR {v2['tn']}/{v2['N']} = {v2['tnr']:.3f} ({ci(v2['tnr_ci'])})  kappa {v2['kappa']:.3f}")
adm2 = admit(SPEC, rates(confusion([r["gold"] for r in test], [r["v2"] for r in test])), role="order")
line(f"  admit: {adm2['admit']}  reasons {adm2['reasons']}")
new_rule_sources = [r["id"] for r in dis if r["cause"] in ("stated_vs_record", "income_arithmetic")][:2]
try:
    guard(new_rule_sources, [r["id"] for r in test])
    line("  guard: clean")
except Leak as e:
    line(f"  guard: {e}")

json.dump({"dev": dv, "test": tv, "admit": adm, "causes": dc, "surface": sa, "construct_v1": cp,
           "escape": eb, "escape_random": ebr, "v2": v2, "admit_v2": adm2,
           "missed_long": [sum(r['long'] for r in caught), len(caught), sum(not r['long'] for r in missed), len(missed)],
           "digest": rec["digest"], "rows": test},
          open(OUT / "lab.json", "w"), indent=1, default=str)
line()
line("wrote out/lab.json")
