"""Chapter 18 lab: validate and correct the fee judge.

Prints every number the chapter uses and writes out/lab.json. Reader gold and
judge verdicts are SIMULATED (fixture.py, seed 2026). Truss computations are real.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import (
    build_production, draw_labeled, reserved_dev_ids, reserved_dev_kinds,
    describe, confusion_counts, N_JUDGED, N_LABELED, SEED,
)
from truss.reportcard import (
    cohen_kappa, kappa_interval, confusion_by_segment, rogan_gladen,
    rogan_gladen_interval, ppi_interval, human_only_interval, as_indicator,
    leak_ids, kind_mix, total_variation, invariance_split, sensitivity_flip,
    build_card, admit_decide,
)
from truss.judge import confusion, rates
from truss.fields import wilson

OUT = {}


def head(s):
    print("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)


def pct(x):
    return "nan" if x != x else f"{100 * x:.2f}%"


def show_cm(label, rows):
    c = confusion_counts(rows)
    print(f"  {label}: n={c['n']}  TP {c['tp']}  FN {c['fn']}  FP {c['fp']}  TN {c['tn']}")
    return c


traces = build_production()
labeled, unlabeled_only = draw_labeled(traces)
# PPI uses the labelled gold against the judge on those same items, plus the
# judge on the complementary traces. The raw rate uses every judged trace.
all_judge = [t["judge"] for t in traces]
labeled_gold = [t["gold"] for t in labeled]
labeled_judge = [t["judge"] for t in labeled]
unlab_judge = [t["judge"] for t in unlabeled_only]


head("1. Fixture (SIMULATED): 2,400 production fee traces, seed 2026")
d = describe(traces)
print(f"traces {d['first']} to {d['last']}: {d['n']}")
print(f"gold fails {d['gold_fail']}/{d['n']} = {pct(d['gold_rate'])}")
print(f"judge fails {d['judge_fail']}/{d['n']} = {pct(d['judge_rate'])}")
print("lang:", d["lang"])
print("kinds:", d["kinds"])
print(f"next production ID after last fee trace: t-{int(d['last'].split('-')[1]) + 5:06d} would be the next fee slot; "
      f"all-flow next after the window is recorded in the ledger from this last ID.")
OUT["fixture"] = d
OUT["next_fee_id"] = f"t-{int(d['last'].split('-')[1]) + 5:06d}"


head("2. Labelled draw: 300 traces, simple random sample")
ld = describe(labeled)
print(f"labeled {ld['first']} .. sample of {ld['n']}")
print(f"gold fails {ld['gold_fail']}/{ld['n']} = {pct(ld['gold_rate'])}")
print(f"judge fails {ld['judge_fail']}/{ld['n']} = {pct(ld['judge_rate'])}")
print("lang:", ld["lang"])
cm_l = show_cm("labeled", labeled)
OUT["labeled"] = {**ld, "confusion": cm_l}


head("3. Agreement, kappa, TPR and TNR on the 300")
cm = confusion(labeled_gold, labeled_judge)
rt = rates(cm)
kap = kappa_interval(labeled_gold, labeled_judge, n_boot=2000, seed=SEED)
print(f"  confusion: TP {cm['tp']} FN {cm['fn']} FP {cm['fp']} TN {cm['tn']} "
      f"abstain_pos {cm['abstain_pos']} abstain_neg {cm['abstain_neg']}")
print(f"  TPR {cm['tp']}/{rt['P']} = {pct(rt['tpr'])}  Wilson {pct(rt['tpr_ci'][0])} to {pct(rt['tpr_ci'][1])}")
print(f"  TNR {cm['tn']}/{rt['N']} = {pct(rt['tnr'])}  Wilson {pct(rt['tnr_ci'][0])} to {pct(rt['tnr_ci'][1])}")
print(f"  raw agreement {(cm['tp']+cm['tn'])}/{len(labeled)} = {pct((cm['tp']+cm['tn'])/len(labeled))}")
print(f"  kappa {kap['kappa']:.4f}  bootstrap 95% interval {kap['ci'][0]:.4f} to {kap['ci'][1]:.4f}  ({kap['n_boot']} draws)")
# Also report the first 200 of the labelled draw, matching the brief's 200-label lab.
first200 = labeled[:200]
cm200 = confusion([t["gold"] for t in first200], [t["judge"] for t in first200])
rt200 = rates(cm200)
kap200 = kappa_interval([t["gold"] for t in first200], [t["judge"] for t in first200], n_boot=2000, seed=SEED)
print(f"  first-200 kappa {kap200['kappa']:.4f}  (TP {cm200['tp']} FN {cm200['fn']} FP {cm200['fp']} TN {cm200['tn']})")
print(f"  first-200 TPR {pct(rt200['tpr'])}  TNR {pct(rt200['tnr'])}")
OUT["agreement"] = {
    "cm": cm, "rates": {k: rt[k] for k in rt},
    "kappa": kap["kappa"], "kappa_ci": kap["ci"],
    "first200": {"cm": cm200, "rates": {k: rt200[k] for k in rt200},
                 "kappa": kap200["kappa"], "kappa_ci": kap200["ci"]},
}


head("4. Confusion by segment (language and kind)")
seg_lang = confusion_by_segment([t["lang"] for t in labeled], labeled_gold, labeled_judge)
for s in ("en", "es"):
    if s in seg_lang:
        v = seg_lang[s]
        print(f"  lang={s} n={v['n']} TP {v['tp']} FN {v['fn']} FP {v['fp']} TN {v['tn']} "
              f"TPR {pct(v['tpr'])} TNR {pct(v['tnr'])} kappa {v['kappa']:.3f}")
print(f"  language accuracy gap {seg_lang.get('_max_gap', float('nan')):.4f}")
seg_kind = confusion_by_segment([t["kind"] for t in labeled], labeled_gold, labeled_judge)
for s, v in sorted(((k, x) for k, x in seg_kind.items() if not k.startswith("_")), key=lambda kv: -kv[1]["n"]):
    print(f"  kind={s} n={v['n']} TP {v['tp']} FN {v['fn']} FP {v['fp']} TN {v['tn']} "
          f"TPR {pct(v['tpr'])} TNR {pct(v['tnr'])}")
seg_len = confusion_by_segment([t["length"] for t in labeled], labeled_gold, labeled_judge)
for s in ("short", "long"):
    if s in seg_len:
        v = seg_len[s]
        print(f"  length={s} n={v['n']} TPR {pct(v['tpr'])} TNR {pct(v['tnr'])}")
print(f"  length accuracy gap {seg_len.get('_max_gap', float('nan')):.4f}")
OUT["segments"] = {
    "lang": {k: v for k, v in seg_lang.items()},
    "kind": {k: v for k, v in seg_kind.items()},
    "length": {k: v for k, v in seg_len.items()},
}


head("5. Raw judge rate on 2,400 and Rogan-Gladen correction")
raw_k = d["judge_fail"]
raw_n = d["n"]
raw = raw_k / raw_n
raw_ci = wilson(raw_k, raw_n)
print(f"  raw judge fail rate {raw_k}/{raw_n} = {pct(raw)}  Wilson {pct(raw_ci[0])} to {pct(raw_ci[1])}")
print(f"  calibration TPR {rt['tpr']:.4f}  TNR {rt['tnr']:.4f}")
try:
    rg_point = rogan_gladen(raw, rt["tpr"], rt["tnr"])
    print(f"  Rogan-Gladen point {pct(rg_point['p'])}  (clipped {pct(rg_point['p_clipped'])}, Youden {rg_point['youden']:.4f})")
except ValueError as e:
    rg_point = {"p": float("nan"), "error": str(e)}
    print("  Rogan-Gladen refused:", e)
rg = rogan_gladen_interval(labeled_gold, labeled_judge, all_judge, n_boot=2000, seed=SEED)
print(f"  Rogan-Gladen bootstrap 95% interval {pct(rg['ci'][0])} to {pct(rg['ci'][1])}  "
      f"(kept {rg['kept']}/{rg['n_boot']})")
print(f"  true planted rate {d['gold_fail']}/{d['n']} = {pct(d['gold_rate'])}  (not available in production; fixture only)")
OUT["raw"] = {"k": raw_k, "n": raw_n, "p": raw, "ci": raw_ci}
OUT["rg"] = {k: rg[k] for k in rg if k not in ("cm", "rates")}


head("6. Prediction-powered inference (300 human + 2,400 judge)")
y = as_indicator(labeled_gold)
f_n = as_indicator(labeled_judge)
f_N = as_indicator(all_judge)
# Classical PPI uses the judge on the unlabelled complement, but Harbor's
# published judge rate is the census of all 2,400. Using the census as f_N
# includes the labelled items once in f_N and once (negatively) in the
# rectifier; the two appearances cancel, so the estimator is unchanged if we
# pass all 2,400. We pass all 2,400 to match the brief.
pp = ppi_interval(y, f_n, f_N)
hum = human_only_interval(y)
hum_w = hum["wilson"]
print(f"  human-only {ld['gold_fail']}/{ld['n']} = {pct(hum['p'])}  "
      f"Wald {pct(hum['ci'][0])} to {pct(hum['ci'][1])}  "
      f"Wilson {pct(hum_w[0])} to {pct(hum_w[1])}")
print(f"  judge on labelled {ld['judge_fail']}/{ld['n']} = {pct(pp['judge_labeled'])}")
print(f"  judge on all {raw_k}/{raw_n} = {pct(pp['judge_unlabeled'])}")
print(f"  rectifier {pp['rectifier']:+.5f} ({pp['rectifier']*100:+.2f} points)")
print(f"  PPI {pct(pp['p'])}  interval {pct(pp['ci'][0])} to {pct(pp['ci'][1])}  se {pp['se']:.5f}")
print(f"  human-only Wald width {hum['ci'][1]-hum['ci'][0]:.5f}")
print(f"  human-only Wilson width {hum_w[1]-hum_w[0]:.5f}")
print(f"  PPI width {pp['ci'][1]-pp['ci'][0]:.5f}")
print(f"  width ratio PPI/human-Wald {(pp['ci'][1]-pp['ci'][0])/(hum['ci'][1]-hum['ci'][0]):.3f}")
OUT["ppi"] = pp
OUT["human_only"] = hum


head("7. Leak check and kind-mix against the Chapter 16 development set")
reserved_ids = reserved_dev_ids()
reserved_kinds = reserved_dev_kinds()
leaked = leak_ids([t["trace_id"] for t in labeled], reserved_ids)
tv = total_variation(kind_mix(t["kind"] for t in labeled), kind_mix(reserved_kinds))
tv_prod = total_variation(kind_mix(t["kind"] for t in traces), kind_mix(reserved_kinds))
print(f"  leaked IDs: {leaked or 'none'}")
print(f"  TV(labeled, reserved-dev-kinds) = {tv:.4f}")
print(f"  TV(production, reserved-dev-kinds) = {tv_prod:.4f}")
OUT["leak"] = leaked
OUT["kind_tv_labeled"] = tv
OUT["kind_tv_production"] = tv_prod
OUT["reserved_kind_mix"] = kind_mix(reserved_kinds)
OUT["labeled_kind_mix"] = kind_mix(t["kind"] for t in labeled)


head("8. Invariance (length) and sensitivity (five flipped gold fails)")
inv = invariance_split(y, f_n, f_N, [t["length"] for t in labeled])
print(f"  PPI by length: " + ", ".join(
    f"{k} n={sum(1 for t in labeled if t['length']==k)} p={pct(inv[k]['p'])}"
    for k in ("short", "long") if k in inv
))
print(f"  invariance range {inv['_range']:.5f}")
sens = sensitivity_flip(y, f_n, f_N, n_flip=5, seed=SEED)
print(f"  sensitivity: flipped {sens['n_flip']} labelled passes to fail; "
      f"PPI moved {sens['moved']:+.5f} "
      f"({pct(sens['baseline']['p'])} -> {pct(sens['perturbed']['p'])})")
OUT["invariance"] = {k: (inv[k] if not isinstance(inv[k], dict) else {kk: inv[k][kk] for kk in inv[k]})
                     for k in inv}
OUT["sensitivity"] = {
    "n_flip": sens["n_flip"], "moved": sens["moved"],
    "baseline": sens["baseline"]["p"], "perturbed": sens["perturbed"]["p"],
}


head("9. Judge Report Card and decide-role admission")
card = build_card(
    labeled_gold, labeled_judge, all_judge,
    judge="fee-judge-v1", metric_card="MC-02 v1.1",
    segments=[t["lang"] for t in labeled],
    val_ids=[t["trace_id"] for t in labeled],
    reserved_ids=reserved_ids,
    val_kinds=[t["kind"] for t in labeled],
    reserved_kinds=reserved_kinds,
    invariance_key=[t["length"] for t in labeled],
    n_boot=2000, seed=SEED,
)
decision = admit_decide(card)
print(f"  judge {card.judge} on {card.metric_card}")
print(f"  n_labeled {card.n_labeled}  n_judged {card.n_judged}")
print(f"  kappa {card.kappa:.4f}  ({card.kappa_ci[0]:.4f} to {card.kappa_ci[1]:.4f})")
print(f"  raw {pct(card.raw_rate)}  PPI {pct(card.ppi['p'])}  RG {pct(card.rg['p'])}")
print(f"  leak {card.leak or 'none'}  kind TV {card.kind_tv_vs_reserved:.4f}")
print(f"  invariance range {card.invariance_range:.5f}  sensitivity moved {card.sensitivity_moved:+.5f}")
print(f"  drift: {card.drift}")
print(f"  admit {decision['admit']}  role {decision['role']}")
print(f"  reasons: {decision['reasons'] or 'none'}")
OUT["card"] = {
    "judge": card.judge, "metric_card": card.metric_card,
    "n_labeled": card.n_labeled, "n_judged": card.n_judged,
    "kappa": card.kappa, "kappa_ci": card.kappa_ci,
    "raw_rate": card.raw_rate, "raw_ci": card.raw_ci,
    "ppi": card.ppi["p"], "ppi_ci": card.ppi["ci"],
    "rg": card.rg["p"], "rg_ci": card.rg["ci"],
    "kind_tv": card.kind_tv_vs_reserved,
    "invariance_range": card.invariance_range,
    "sensitivity_moved": card.sensitivity_moved,
    "drift": card.drift,
    "admit": decision["admit"], "role": decision["role"],
    "reasons": decision["reasons"],
}

out_path = HERE / "out" / "lab.json"
out_path.write_text(json.dumps(OUT, indent=2, default=str))
print(f"\nwrote {out_path}")
