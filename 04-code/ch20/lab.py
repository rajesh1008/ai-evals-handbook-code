"""Chapter 20 lab: confidence, calibration and routing for hardship decisions.

Prints every number the chapter uses and writes out/lab.json. No model is
called. Decisions, gold and all three confidence fields are SIMULATED (see
fixture.py, seed 2026). Truss computations are real.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

import truss
from fixture import (MINUTES, MODEL_PIN_A, MODEL_PIN_B, POLICY_DIGEST, SEED, outcome,
                     status_quo, world)
from truss.calibration import (apply_map, auroc, brier, brier_decomposition, calibration_map,
                               cp_threshold, crc_threshold, degenerate, ece, feasibility_floor,
                               map_valid_for, post_review_estimate, reliability_table,
                               simulate_routing)
from truss.rates import upper_bound, wilson

OUT: dict = {"seed": SEED, "truss": truss.__version__}
T_AUTO, T_REFUSE = 0.956, 0.85
THREE = (0.93, 0.956, 0.99)
CAPACITY = 720.0   # officer minutes a week for hardship review (Grace and Ben, six hours each)


def head(s):
    print("\n" + "=" * 96 + "\n" + s + "\n" + "=" * 96)


def pct(x, d=1):
    return "nan" if x != x else f"{100 * x:.{d}f}%"


from lab_common import digest


def present(S, f):
    return [c for c in S if c[f] is not None]


def score_all(S, cmap, field="logprob"):
    for c in S:
        c["score"] = apply_map(cmap, c[field]) if c[field] is not None else None


W = world()
fit, jan = W["fit"], W["jan"]
live = [c for wk in W["live"].values() for c in wk]

head("1. The sets (SIMULATED decisions; gold is planted correctness)")
for name, S in (("fit: quota random, 27 Sep to 26 Dec 2027", fit), ("January calibration draw, 3 to 14 Jan 2028", jan),
                ("live routing, 17 Jan to 13 Feb 2028", live)):
    k = sum(not c["correct"] for c in S)
    lo, hi = wilson(len(S) - k, len(S))
    print(f"  {name}: n={len(S)} offers={sum(c['kind']=='offer' for c in S)} declines={sum(c['kind']=='decline' for c in S)} "
          f"wrong={k} ({pct(k/len(S))}) accuracy {pct(1-k/len(S))} (Wilson {pct(lo)} to {pct(hi)})")
print(f"  January IDs {jan[0]['trace_id']} .. {jan[-1]['trace_id']}; live IDs {live[0]['trace_id']} .. {live[-1]['trace_id']}")
OUT["sets"] = {"fit": len(fit), "jan": len(jan), "live": len(live),
               "fit_wrong": sum(not c["correct"] for c in fit), "jan_wrong": sum(not c["correct"] for c in jan),
               "live_wrong": sum(not c["correct"] for c in live)}

head("2. Evidence is not probability: the citation field")
both = fit + jan
for has in (True, False):
    T = [c for c in both if c["citation"] == has]
    k = sum(c["correct"] for c in T)
    print(f"  citation present={has}: n={len(T)} right {k} = {pct(k/len(T))}")
W_ = [c for c in both if not c["correct"]]
print(f"  wrong decisions citing policy and record: {sum(c['citation'] for c in W_)}/{len(W_)} = {pct(sum(c['citation'] for c in W_)/len(W_))}")
OUT["citation"] = {str(h): [sum(c["correct"] for c in both if c["citation"] == h), sum(c["citation"] == h for c in both)] for h in (True, False)}
OUT["citation"]["wrong_citing"] = [sum(c["citation"] for c in W_), len(W_)]

head("3. Three confidence fields on the fit set and the January set")
OUT["fields"] = {}
for name, S in (("fit", fit), ("jan", jan)):
    for f in ("verbal", "logprob", "judge"):
        T = present(S, f)
        x = [c[f] for c in T]; y = [c["correct"] for c in T]
        d = brier_decomposition(x, y)
        r = {"n": len(T), "ece": ece(x, y), "ece_q": ece(x, y, 10, "quantile"), "auroc": auroc(x, y),
             "brier": brier(x, y), "resolution": d["resolution"], "reliability": d["reliability"],
             "mean_conf": sum(x) / len(x), "acc": sum(y) / len(y), "degenerate": degenerate(x)}
        OUT["fields"][f"{name}:{f}"] = r
        print(f"  {name:4s} {f:8s} n={r['n']:4d} mean conf {r['mean_conf']:.3f} accuracy {r['acc']:.3f} "
              f"ECE {r['ece']:.4f} (quantile {r['ece_q']:.4f}) AUROC {r['auroc']:.3f} Brier {r['brier']:.4f} "
              f"resolution {r['resolution']:.4f} degenerate={r['degenerate']}")
V = [c["verbal"] for c in both]
from collections import Counter
vc = Counter(V)
print("  verbalised values:", {f"{k:.2f}": v for k, v in sorted(vc.items())})
OUT["verbal_values"] = {f"{k:.2f}": v for k, v in sorted(vc.items())}

head("4. Segment view: where each field is confidently wrong (fit + January, wrong decisions)")
OUT["segments"] = {}
for seg in ("anniversary", "stated_work", "multi_loan", "none"):
    T = [c for c in both if not c["correct"] and ((seg == "none" and not c["segments"]) or seg in c["segments"])]
    if not T:
        continue
    row = {"n": len(T)}
    for f in ("verbal", "logprob", "judge"):
        xs = [c[f] for c in T if c[f] is not None]
        row[f] = sum(xs) / len(xs) if xs else float("nan")
    OUT["segments"][seg] = row
    print(f"  {seg:12s} wrong n={len(T):3d} mean verbal {row['verbal']:.3f} logprob {row['logprob']:.3f} judge {row['judge']:.3f}")

head("5. Recalibration map on the fit set (logprob -> Platt), bound to model pin and policy")
F = present(fit, "logprob")
cmap = calibration_map([c["logprob"] for c in F], [c["correct"] for c in F], MODEL_PIN_A, POLICY_DIGEST,
                       digest([c["logprob"] for c in F]), "logprob")
print(f"  map digest {cmap['digest']} kind {cmap['kind']} params a={cmap['params'][0]:.4f} b={cmap['params'][1]:.4f} "
      f"n={cmap['n']} pin {cmap['model_pin']} policy {cmap['policy_digest']}")
for S in (fit, jan, live):
    score_all(S, cmap)
J = present(jan, "logprob")
xr = [c["logprob"] for c in J]; xc = [c["score"] for c in J]; y = [c["correct"] for c in J]
print(f"  January: raw ECE {ece(xr, y):.4f} -> calibrated ECE {ece(xc, y):.4f}; AUROC raw {auroc(xr, y):.3f} calibrated {auroc(xc, y):.3f} (a monotone map keeps the ranking)")
rt_raw = reliability_table(xr, y, 10); rt_cal = reliability_table(xc, y, 10)
for r in rt_cal:
    print(f"    calibrated bin ({r['lo']:.1f},{r['hi']:.1f}] n={r['n']:3d} conf {r['conf']:.3f} acc {r['acc']:.3f}")
OUT["map"] = cmap
OUT["jan_cal"] = {"ece_raw": ece(xr, y), "ece_cal": ece(xc, y), "auroc": auroc(xc, y),
                  "rt_raw": rt_raw, "rt_cal": rt_cal}
# reliability diagrams of all three on January for the figure
OUT["rt"] = {f: reliability_table([c[f] for c in present(jan, f)], [c["correct"] for c in present(jan, f)], 10)
             for f in ("verbal", "logprob", "judge")}
OUT["rt"]["calibrated"] = rt_cal

head("6. Thresholds from the gold set: CRC and an exact bound on the fit set (unflagged cases)")
U = [c for c in fit if c["score"] is not None and not c["flags"]]
s = [c["score"] for c in U]; e = [not c["correct"] for c in U]
mu = sum(not c["correct"] for c in fit) / len(fit)
OUT["thresholds"] = {}
for a in (0.005, 0.01, 0.02):
    crc = crc_threshold(s, e, a); cp = cp_threshold(s, e, a)
    OUT["thresholds"][str(a)] = {"crc": crc, "cp": cp, "floor": feasibility_floor(mu, a)}
    print(f"  alpha {pct(a)}: CRC {('t=%.4f auto %d (%s), errors %d, bound %.4f' % (crc['t'], crc['n_auto'], pct(crc['share']), crc['errors'], crc['bound'])) if crc else 'infeasible'}; "
          f"exact 95% bound {('t=%.4f auto %d, bound %.4f' % (cp['t'], cp['n_auto'], cp['bound'])) if cp else 'infeasible on this set'}; "
          f"feasibility floor {pct(feasibility_floor(mu, a))} of all decisions withheld (base error {pct(mu)})")
for k in (0, 1, 2):
    from truss.rates import traces_needed
    print(f"  auto-route cases needed for an exact 95% bound under 1% with {k} errors: {traces_needed(0.01, k)}")
OUT["needed_1pct"] = [traces_needed(0.01, k) for k in (0, 1, 2)]

head("7. Three thresholds on the January set (t_refuse 0.85; refuse also takes missing scores)")
OUT["jan_routes"] = {}
sq = simulate_routing(jan, 0, 0, outcome, MINUTES, policy=status_quo)
allr = simulate_routing(jan, 0, 0, outcome, MINUTES, policy=lambda c: ("review", "all"))
for name, r in (("status quo (offers reviewed, declines sent)", sq), ("review everything", allr)):
    print(f"  {name:44s} auto {pct(r['share']['auto'])} review {pct(r['share']['review'])} refuse {pct(r['share']['refuse'])} "
          f"post-review {r['post_review_wrong']}/{r['n']} = {pct(r['post_review_error'], 2)} minutes {r['officer_minutes']:.0f}")
OUT["jan_routes"]["status_quo"] = sq; OUT["jan_routes"]["all_review"] = allr
for t in THREE:
    r = simulate_routing(jan, t, T_REFUSE, outcome, MINUTES)
    A = [c for c in jan if c["score"] is not None and c["score"] >= t and not c["flags"]]
    k = sum(not c["correct"] for c in A)
    r["auto_bound"] = upper_bound(k, len(A))
    OUT["jan_routes"][str(t)] = r
    print(f"  t_auto {t:.3f}{' (chosen)' if t == T_AUTO else '         '}                         auto {pct(r['share']['auto'])} review {pct(r['share']['review'])} "
          f"refuse {pct(r['share']['refuse'])} post-review {r['post_review_wrong']}/{r['n']} = {pct(r['post_review_error'], 2)} "
          f"auto errors {k}/{len(A)} (exact 95% bound {pct(r['auto_bound'], 2)}) minutes {r['officer_minutes']:.0f} reasons {r['reasons']}")

head("8. Threshold versus review load at three traffic levels (January mix scaled; capacity 720 min/week)")
OUT["load"] = {}
weekly_at_10 = 140
for traffic in (0.10, 0.25, 0.50):
    scale = traffic / 0.10 * weekly_at_10 / len(jan)
    rows = {}
    for name, kw in (("status_quo", {"policy": status_quo}), ("all_review", {"policy": lambda c: ("review", "all")}),
                     ("0.93", {}), ("0.956", {}), ("0.99", {})):
        t = float(name) if name[0] == "0" else 0
        base = simulate_routing(jan, t, T_REFUSE, outcome, MINUTES, **kw)
        minutes = base["officer_minutes"] * scale
        r = simulate_routing(jan, t, T_REFUSE, outcome, MINUTES, capacity_minutes=CAPACITY / scale, **kw)
        rows[name] = {"minutes_week": minutes, "hours_week": minutes / 60, "overloaded": r["overloaded"],
                      "post_review_error": r["post_review_error"], "cost_week": minutes / 60 * 60.0}
        print(f"  traffic {pct(traffic,0):>4s} {name:10s} officer {minutes/60:5.1f} h/week {'OVER' if r['overloaded'] else 'ok  '} "
              f"post-review {pct(r['post_review_error'], 2)} review cost ${minutes/60*60:,.0f}/week")
    OUT["load"][str(traffic)] = rows
grid = []
for i in range(0, 14):
    t = round(0.93 + 0.005 * i, 3)
    r = simulate_routing(jan, t, T_REFUSE, outcome, MINUTES)
    grid.append({"t": t, "auto": r["share"]["auto"], "review": r["share"]["review"], "refuse": r["share"]["refuse"],
                 "minutes": r["officer_minutes"], "post": r["post_review_error"]})
OUT["grid"] = grid

head("9. Live routing, 17 Jan to 13 Feb 2028 (t_auto 0.956, t_refuse 0.85; map %s)" % cmap["digest"])
OUT["live"] = {}
lab_alloc = {"auto": 30, "review": 20, "refuse": 10}
import random
rng = random.Random(SEED + 20)
strata_tot = {r: [0, 0] for r in lab_alloc}
counts_tot = {r: 0 for r in lab_alloc}
for wk, S in W["live"].items():
    score_all(S, cmap)
    r = simulate_routing(S, T_AUTO, T_REFUSE, outcome, MINUTES)
    OUT["live"][wk] = r
    print(f"  week of {wk}: n={r['n']} auto {pct(r['share']['auto'])} review {pct(r['share']['review'])} refuse {pct(r['share']['refuse'])} "
          f"post-review {r['post_review_wrong']} wrong; minutes {r['officer_minutes']:.0f}")
    from truss.calibration import route
    for rname, need in lab_alloc.items():
        pool = [c for c in S if route(c["score"], c["flags"], T_AUTO, T_REFUSE)[0] == rname]
        counts_tot[rname] += len(pool)
        pick = rng.sample(pool, min(need, len(pool)))
        strata_tot[rname][0] += sum(outcome(c, rname) for c in pick)
        strata_tot[rname][1] += len(pick)
tot = simulate_routing(live, T_AUTO, T_REFUSE, outcome, MINUTES)
OUT["live_total"] = tot
print(f"  four weeks, launch condition (every routed decision second-read by an officer): n={tot['n']} auto {pct(tot['share']['auto'])} review {pct(tot['share']['review'])} "
      f"refuse {pct(tot['share']['refuse'])}; post-review {tot['post_review_wrong']}/{tot['n']} = {pct(tot['post_review_error'], 2)}; "
      f"by route {tot['wrong']} route error auto {pct(tot['route_error']['auto'], 2)} review {pct(tot['route_error']['review'], 2)} refuse {pct(tot['route_error']['refuse'], 2)}")
print(f"  exact 95% upper bound on 4/{tot['n']}: {pct(upper_bound(tot['post_review_wrong'], tot['n']), 2)}")
N = sum(counts_tot.values())
strata = {r: (counts_tot[r] / N, strata_tot[r][0], strata_tot[r][1]) for r in lab_alloc}
est = post_review_estimate(strata)
print(f"  steady-state design after launch, stratified 60 labels a week (30 auto, 20 review, 10 refuse), same four weeks: labels {dict((r, strata_tot[r]) for r in lab_alloc)} -> estimate {pct(est['rate'], 2)} "
      f"(approx 95% {pct(est['lo'], 2)} to {pct(est['hi'], 2)})")
sq_live = simulate_routing(live, 0, 0, outcome, MINUTES, policy=status_quo)
all_live = simulate_routing(live, 0, 0, outcome, MINUTES, policy=lambda c: ("review", "all"))
print(f"  same four weeks under the status quo: {sq_live['post_review_wrong']}/{sq_live['n']} = {pct(sq_live['post_review_error'], 2)} "
      f"(declines sent: {sq_live['wrong']['auto']} wrong); review everything: {all_live['post_review_wrong']}/{all_live['n']} = {pct(all_live['post_review_error'], 2)}; "
      f"officer minutes status quo {sq_live['officer_minutes']:.0f}, routed {tot['officer_minutes']:.0f}, all {all_live['officer_minutes']:.0f}")
from truss.calibration import route as _route
def _final_wrong(c):
    return outcome(c, _route(c["score"], c["flags"], T_AUTO, T_REFUSE)[0])
off_wrong = [c for c in live if c["kind"] == "offer"]
ow = sum(_final_wrong(c) for c in off_wrong)
dec = [c for c in live if c["kind"] == "decline"]
dw = sum(_final_wrong(c) for c in dec)
dsq = sum(outcome(c, "auto") for c in dec)
print(f"  wrongful declines reaching a borrower: routed {dw}/{len(dec)}; status quo {dsq}/{len(dec)}")
print(f"  wrong offers reaching a borrower: {ow}/{len(off_wrong)} offers = {pct(ow/len(off_wrong), 2)} "
      f"(exact 95% bound {pct(upper_bound(ow, len(off_wrong)), 2)}; Victor's <0.5% widening gate is not shown by four weeks)")
OUT["live_est"] = {"strata": strata, "est": est, "status_quo": sq_live, "all_review": all_live,
                   "wrong_offers": [ow, len(off_wrong)], "wrong_declines": [dw, len(dec)], "wrong_declines_sq": [dsq, len(dec)], "bound": upper_bound(tot["post_review_wrong"], tot["n"])}

head("10. Model change, Monday 14 February 2028 (rc-0214-1, pin %s)" % MODEL_PIN_B)
post = [c for wk in W["post"].values() for c in wk]
reasons = map_valid_for(cmap, MODEL_PIN_B, POLICY_DIGEST)
print(f"  map {cmap['digest']} valid for new pin? reasons={reasons}")
score_all(post, cmap)
pinned = simulate_routing(post, T_AUTO, T_REFUSE, outcome, MINUTES, map_reasons=reasons)
unpinned = simulate_routing(post, T_AUTO, T_REFUSE, outcome, MINUTES)
print(f"  pinned (fail closed): auto {pct(pinned['share']['auto'])} review {pct(pinned['share']['review'])} refuse {pct(pinned['share']['refuse'])} "
      f"post-review {pct(pinned['post_review_error'], 2)} minutes/week {pinned['officer_minutes']/3:.0f}")
print(f"  unpinned (old map on new scores): auto {pct(unpinned['share']['auto'])} review {pct(unpinned['share']['review'])} "
      f"refuse {pct(unpinned['share']['refuse'])} post-review {pct(unpinned['post_review_error'], 2)} auto errors {unpinned['wrong']['auto']}/{unpinned['count']['auto']}")
R = present(W["recal"], "logprob")
xb = [c["logprob"] for c in R]; yb = [c["correct"] for c in R]
old_scores = [apply_map(cmap, x) for x in xb]
print(f"  recalibration draw 14 to 25 Feb: n={len(W['recal'])} ({len(R)} with a log-probability); ECE under the old map {ece(old_scores, yb):.4f}")
cmap_b = calibration_map(xb, yb, MODEL_PIN_B, POLICY_DIGEST, digest(xb), "logprob")
new_scores = [apply_map(cmap_b, x) for x in xb]
print(f"  new map {cmap_b['digest']} a={cmap_b['params'][0]:.4f} b={cmap_b['params'][1]:.4f}; in-sample ECE {ece(new_scores, yb):.4f}")
wk = W["post"]["2028-02-28"]
score_all(wk, cmap_b)
r28 = simulate_routing(wk, T_AUTO, T_REFUSE, outcome, MINUTES)
print(f"  week of 28 Feb on the new map: auto {pct(r28['share']['auto'])} review {pct(r28['share']['review'])} refuse {pct(r28['share']['refuse'])} "
      f"post-review {r28['post_review_wrong']}/{r28['n']}")
OUT["change"] = {"reasons": reasons, "pinned": pinned, "unpinned": unpinned, "ece_old": ece(old_scores, yb),
                 "map_b": cmap_b, "ece_new": ece(new_scores, yb), "week_28": r28,
                 "rt_old": reliability_table(old_scores, yb, 10), "rt_new": reliability_table(new_scores, yb, 10)}

head("11. Costs (officer time at $60 an hour; labels at $13.90; both illustrative)")
c_jan = 400 * 13.90
c_recal = 300 * 13.90
print(f"  January calibration draw 400 labels: ${c_jan:,.0f}; February recalibration draw 300 labels: ${c_recal:,.0f}")
print(f"  officer review at 10% traffic: status quo {sq_live['officer_minutes']/4/60:.1f} h/week (${sq_live['officer_minutes']/4:,.0f}); "
      f"routed {tot['officer_minutes']/4/60:.1f} h/week (${tot['officer_minutes']/4:,.0f}); fail-closed weeks {pinned['officer_minutes']/3/60:.1f} h/week")
OUT["costs"] = {"jan": c_jan, "recal": c_recal}

OUT["dist"] = {f: [[c[f], c["correct"]] for c in jan if c[f] is not None] for f in ("verbal", "logprob", "judge")}
OUT["dist"]["calibrated"] = [[c["score"], c["correct"]] for c in jan if c["score"] is not None]
fitgrid = []
for i in range(0, 41):
    t = round(0.80 + 0.005 * i, 3)
    A = [c for c in U if c["score"] >= t]
    k = sum(not c["correct"] for c in A)
    fitgrid.append({"t": t, "n_auto": len(A), "errors": k, "share": len(A) / len(fit),
                    "crc": (k + 1) / (len(A) + 1) if A else 1.0, "cp": upper_bound(k, len(A)) if A else 1.0})
OUT["fitgrid"] = fitgrid
OUT["feasibility"] = {"mu": mu, "floor_1pct": feasibility_floor(mu, 0.01)}
(HERE / "out").mkdir(exist_ok=True)
json.dump(OUT, open(HERE / "out" / "lab.json", "w"), indent=1, default=str)
print("\nwrote out/lab.json")
