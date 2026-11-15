"""Chapter 12 Lab: Harbor's golden set v1.0 and v1.1, June 2027.

Reads the fixture (golden.py, SIMULATED and labelled so) and the two real model runs' caches
(out/validate.json from synth.py + validate.py, out/leak.json from leak.py). Writes out/lab.json.
"""
import json, random, statistics, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
import truss
from truss import datasets as ds
from truss.rates import wilson, upper_bound, traces_needed
import golden

HERE = Path(__file__).resolve().parent
OUT = {}
GATES = {"common": .95, "uncommon": .85, "hard": .70, "adversarial": .60, "ood": .70}
pct = lambda x: f"{100 * x:.1f}%"


def section(t):
    print(f"\n== {t} ==")


def plant(cases, seed=2026):
    """Plant what an audit should find (SIMULATED): six re-opened duplicate conversations, stale
    labels, and seven cases whose label or reference is wrong so that every build 'fails' them."""
    g = random.Random(seed + 1)
    prod = [c for c in cases if c["source"] == "production"]
    for c in prod:
        c["account"] = f"A-{g.randrange(10**5, 10**6)}"
        c["opened"] = f"2027-{c['labelled_on'][5:7]}-{g.randrange(1, 27):02d}"
    dups = []
    for a in g.sample(prod, 6):
        b = g.choice([x for x in prod if x["flow"] == a["flow"] and x is not a and x not in dups])
        dups += [a, b]
    for a, b in zip(dups[::2], dups[1::2]):
        b.update(account=a["account"], opened=a["opened"][:-2] + f"{min(28, int(a['opened'][-2:]) + 1):02d}")
    stale = [c for c in cases if c["flow"] == "hardship" and c["features"].get("edge") and c["labelled_on"] < "2027-04-01"]
    wrong = stale[:4] + [c for c in prod if c["flow"] == "fee_explanation"][:2] + [c for c in prod if c["flow"] == "payoff_letter"][:1]
    for c in wrong:
        c["broken"] = "stale label" if c["flow"] == "hardship" else ("label from FS-2026-02" if c["flow"] == "fee_explanation" else "stale reference figure")
    return {"dup_pairs": [(a["case_id"], b["case_id"]) for a, b in zip(dups[::2], dups[1::2])], "broken": [c["case_id"] for c in wrong]}


def run_build(cases, name, seed=2026):
    v = golden.verdicts(cases, name, seed)
    for c in cases:
        if c.get("broken"):
            v[c["case_id"]] = False
    return v


cases = golden.build()
truth = plant(cases)

section("1. Golden set v1.0 (assembled Mon 7 June 2027)")
m10 = ds.manifest("harbor-golden", "1.0", cases, "frozen 300, March fee 200, weekly draws 457, incident 153, authored 80, planted 10", truss.__version__)
print(json.dumps({k: m10[k] for k in ("n", "digest", "by_source", "by_slice", "rate_eligible")}))
comp = ds.composition(cases)
for f in golden.FLOWS:
    print(f"  {f:18s}", " ".join(f"{s}={comp[f].get(s, 0):3d}" for s in ds.SLICES), f"total={sum(comp[f].values())}")
OUT["v10"] = m10; OUT["composition"] = comp

section("2. Authored against production (hardship slice)")
hs = [c for c in cases if c["flow"] == "hardship"]
val = json.load(open(HERE / "out/validate.json"))
groups = {"production": [c["features"] for c in hs if c["source"] == "production"],
          "authored": [c["features"] for c in hs if c["source"] == "authored"]}
cmp = {}
for k, fs in groups.items():
    cmp[k] = {f: sum(bool(x[f]) for x in fs) / len(fs) for f in ("two_loans", "prior_relief", "edge", "spanish", "self_employed", "income_missing", "tool_error")}
    cmp[k]["turns"] = statistics.mean(x["turns"] for x in fs)
    cmp[k]["n"] = len(fs)
    cmp[k]["expected_pass"] = statistics.mean(1 - golden.fail_prob(x) for x in fs)
syn = dict(val["features_admitted"]); syn["n"] = val["funnel"]["deduplicated"]
# synthetic cases are first messages; the simulator scores them at the production median turn count
med = statistics.median(x["turns"] for x in groups["production"])
cmp["synthetic"] = dict(syn, turns=None)
g = random.Random(7)
synf = []
for c in json.load(open(HERE / "out/synth_cases.json")):
    if c.get("admitted"):
        r = c["raw"]
        synf.append({"two_loans": len(r["loans"]) > 1, "prior_relief": r["prior_relief"] is not None,
                     "edge": bool(r["prior_relief"]) and 10 <= r["prior_relief"]["months_ago"] <= 14,
                     "spanish": r["language"] == "es", "self_employed": r["income_type"] == "self_employed",
                     "income_missing": r["income_monthly"] in (None, 0), "tool_error": False, "turns": med})
cmp["synthetic"]["expected_pass"] = statistics.mean(1 - golden.fail_prob(x) for x in synf)
for k, v in cmp.items():
    print(f"  {k:10s} n={v['n']:3d} two_loans={pct(v['two_loans'])} prior={pct(v['prior_relief'])} edge={pct(v['edge'])} "
          f"spanish={pct(v['spanish'])} self_emp={pct(v['self_employed'])} no_income={pct(v['income_missing'])} "
          f"tool_err={pct(v['tool_error'])} turns={'-' if v['turns'] is None else round(v['turns'], 1)} simulated_pass={pct(v['expected_pass'])}")
OUT["sources"] = cmp
OUT["turns"] = {"production": [x["turns"] for x in groups["production"]], "authored": [x["turns"] for x in groups["authored"]]}

section("3. Synthetic cases: what validation removed (real run, see validate.py)")
print(json.dumps({k: val[k] for k in ("funnel", "consistency_reasons", "label_disagree", "label_checked", "near_duplicate_pairs")}))
print("  generator label vs policy label, top pairs:", dict(list(val["label_disagree_pairs"].items())[:3]))
print("  prior relief months_ago among admitted:", val["months_ago"])

section("4. Sensitivity by slice (rate-eligible cases only)")
sens = {}
for s in ds.SLICES:
    n = sum(c["slice"] == s and ds.rate_eligible(c) for c in cases)
    nall = sum(c["slice"] == s for c in cases)
    sens[s] = {"n_rate": n, "n_all": nall, "mdd": ds.mdd(nall, golden.PASS["production"][s]), "bound0": upper_bound(0, nall)}
    print(f"  {s:11s} all={nall:4d} rate-eligible={n:4d} smallest detectable drop={pct(sens[s]['mdd'])} zero-failure bound={pct(sens[s]['bound0'])}")
hp = sum(c["flow"] == "hardship" and ds.rate_eligible(c) for c in cases)
need = {f: traces_needed(.005, f) for f in (0, 1, 2)}
print(f"  hardship rate-eligible: {hp}; one-sided 95% bound with 0/1 failures: {pct(upper_bound(0, hp))} / {pct(upper_bound(1, hp))}")
print(f"  needed for <0.5% with 0/1/2 failures: {need}; weeks at 25 a week: {(need[1] - hp) / 25:.1f}; at 60 a week: {(need[1] - hp) / 60:.1f}")
OUT["sens"] = sens; OUT["hardship"] = {"n": hp, "need": need, "b0": upper_bound(0, hp), "b1": upper_bound(1, hp)}
OUT["mdd_curve"] = {n: ds.mdd(n, .9) for n in (25, 50, 100, 200, 400, 800, 1200, 1600)}

section("5. Slice-by-slice gate: production build against rc-0611-1 (SIMULATED verdicts)")
gate = {}
for b in ("production", "rc-0611-1"):
    v = run_build(cases, b)
    res = [(c["slice"], v[c["case_id"]]) for c in cases if not c.get("planted")]
    gate[b] = ds.slice_gate(res, GATES)
    print(f"  {b:11s} aggregate={pct(gate[b]['aggregate'])} verdict={'PASS' if gate[b]['pass'] else 'HOLD'}")
    for s, r in gate[b]["slices"].items():
        print(f"     {s:11s} {r['k']:4d}/{r['n']:4d} = {pct(r['rate'])}  Wilson [{pct(r['lo'])}, {pct(r['hi'])}]  gate {pct(r['gate'])}  {'pass' if r['pass'] else 'FAIL'}")
OUT["gate"] = gate

section("6. Tuning against the dev split (SIMULATED selection, no model)")
g = random.Random(2026)
SD, RHO = (.82 * .18 / 300) ** .5, .5     # sampling sd of a 300-case split; how much of a parent's luck a variant keeps
true, dev_id, ho_id = .82, 0.0, 0.0
traj = []
for rnd in range(13):
    traj.append({"round": rnd, "dev": true + dev_id, "heldout": true + ho_id, "true": true})
    cands = []
    for _ in range(6):
        t = true + g.gauss(.0005, .004)
        d = RHO * dev_id + (1 - RHO ** 2) ** .5 * g.gauss(0, SD)
        h = RHO * ho_id + (1 - RHO ** 2) ** .5 * g.gauss(0, SD)
        cands.append((t + d, t, d, h))
    best = max(cands)
    if best[0] > true + dev_id:
        true, dev_id, ho_id = best[1], best[2], best[3]
it = {"dev_gain": traj[-1]["dev"] - traj[0]["dev"], "heldout_gain": traj[-1]["heldout"] - traj[0]["heldout"],
      "true_gain": traj[-1]["true"] - traj[0]["true"], "traj": traj}
print(f"  12 rounds x 6 prompt variants, chosen on a 300-case dev split: dev +{100 * it['dev_gain']:.1f} pts, "
      f"held-out {100 * it['heldout_gain']:+.1f} pts, simulator's true change {100 * it['true_gain']:+.1f} pts")
OUT["iterate"] = it

section("7. Version 1.0 to 1.1 (Mon 21 June 2027)")
hist = {b: run_build(cases, b) for b in ("rc-0524-1", "rc-0601-1", "rc-0608-1", "production")}
always = [c["case_id"] for c in cases if not c.get("planted") and not any(hist[b][c["case_id"]] for b in hist)]
byid = {c["case_id"]: c for c in cases}
print(f"  failed by all four builds: {len(always)}; on inspection: {dict(Counter(byid[i].get('broken', 'genuinely hard') for i in always))}")
stale = ds.stale_labels(cases, [{"policy": "HP-2027-04", "effective": "2027-04-01", "flow": "hardship", "feature": "prior_relief"}])
relabel = [cid for cid, _ in stale if byid[cid]["features"]["edge"]]
print(f"  hardship labels written before HP-2027-04 on cases with prior relief: {len(stale)}; re-read: {len(relabel)} change under the calendar-month window")
seen, dup = {}, []
for c in cases:
    if c["source"] == "production":
        k = (c["account"], c["flow"])
        if k in seen and abs(int(seen[k]["opened"][-2:]) - int(c["opened"][-2:])) <= 2 and seen[k]["opened"][:7] == c["opened"][:7]:
            dup.append(c["case_id"])
        seen.setdefault(k, c)
print(f"  re-opened duplicate conversations (same account and flow within two days): {len(dup)}")
v11 = [dict(c) for c in cases if c["case_id"] not in dup]
for c in v11:
    if c["case_id"] in relabel:
        c["label"], c["labelled_on"], c["policy_version"] = "fail-expected-decline-window-recheck", "2027-06-18", "HP-2027-04"
    if c.get("broken") and c["flow"] != "hardship":
        c["broken"] = None; c["labelled_on"] = "2027-06-18"
    c.pop("broken", None) if c["case_id"] in relabel else None
incident = [{"case_id": "g-1201", "trace_id": "t-118842", "flow": "hardship", "source": "incident", "slice": "hard", "split": "progression",
             "label": "pass", "policy_version": "HP-2027-04", "labelled_on": "2027-06-10", "labelled_by": "officer",
             "features": {"spanish": True, "prior_relief": True, "edge": True}, "note": "complaint Wed 9 June 2027: deferral that ended exactly 12 calendar months earlier counted"}]
for j, (mo, lang) in enumerate([(11, "es"), (12, "en"), (13, "es"), (12, "es-two-loans"), ("12, ends 29 Feb 2028 in a leap year", "en")]):
    incident.append({"case_id": f"g-{1202 + j}", "trace_id": None, "flow": "hardship", "source": "incident", "slice": "hard", "split": "progression",
                     "label": "pass", "policy_version": "HP-2027-04", "labelled_on": "2027-06-11", "labelled_by": "officer",
                     "features": {"prior_relief": True, "edge": True}, "note": f"look-alike of t-118842: months_ago {mo}, {lang}"})
v11 += incident
m11 = ds.manifest("harbor-golden", "1.1", v11, "minus 6 duplicate conversations; relabels under HP-2027-04; FS-2026-03 references; plus t-118842 and five look-alikes", truss.__version__)
d = ds.diff(cases, v11)
print(f"  v1.1: n={m11['n']} digest {m11['digest']} (v1.0 {m10['digest']}); added {len(d['added'])}, removed {len(d['removed'])}, changed {len(d['changed'])}, relabelled {len(d['relabelled'])}")
print(f"  rate-eligible: v1.0 {m10['rate_eligible']} -> v1.1 {m11['rate_eligible']} (incident cases never enter a rate)")
OUT["v11"] = m11; OUT["diff"] = {k: len(v) for k, v in d.items()}; OUT["always_fail"] = dict(Counter(byid[i].get('broken', 'genuinely hard') for i in always))
OUT["stale"] = {"candidates": len(stale), "relabelled": len(relabel)}; OUT["dups"] = len(dup)

section("8. Regression and progression sets over four June candidates (SIMULATED)")
prod_v = run_build(v11, "production")
prog = [c["case_id"] for c in v11 if not prod_v.get(c["case_id"], True) or c["split"] == "progression"]
reg = [c["case_id"] for c in v11 if c["case_id"] not in prog]
g = random.Random(2031)
fixed, history, regressions = set(), {c: [] for c in prog}, []
for rc in ("rc-0611-1", "rc-0617-1", "rc-0622-1", "rc-0629-1"):
    fixed |= {c for c in prog if g.random() < .2}
    for c in prog:
        history[c].append(c in fixed or g.random() < .1)
    regressions.append(sum(g.random() < .004 for _ in reg))
grad = ds.graduate(history, 3)
print(f"  start: regression {len(reg)}, progression {len(prog)}; regressions caught per candidate {regressions}; graduated after three straight passes: {len(grad)}")
OUT["regprog"] = {"reg": len(reg), "prog": len(prog), "regressions": regressions, "graduated": len(grad),
                  "pass_by_rc": [sum(h[i] for h in history.values()) for i in range(4)]}

section("9. Five properties of golden set v1.1")
leak = json.load(open(HERE / "out/leak.json"))
reruns = []
for r in range(20):
    gr = random.Random(500 + r)
    reruns.append(statistics.mean(prod_v[c["case_id"]] != (gr.random() < .03) for c in v11 if c["case_id"] in prod_v))
fails = [c for c in v11 if c["case_id"] in prod_v and not prod_v[c["case_id"]]]
coded = sum(random.Random(c["case_id"]).random() < .93 for c in fails)
always_pass = sum(all(hist[b].get(c["case_id"], False) for b in hist) for c in v11)
props = {"validity": f"{len(always)} always-fail cases audited, {len(always) - OUT['always_fail'].get('genuinely hard', 0)} were label or reference faults; {len(relabel)} stale labels re-read",
         "reliability": f"aggregate pass rate across 20 reruns at a 3% per-case flip rate (assumed): sd {100 * statistics.pstdev(reruns):.2f} pts",
         "sensitivity": f"smallest detectable drop: common {pct(sens['common']['mdd'])}, adversarial {pct(sens['adversarial']['mdd'])}, hardship bound {pct(upper_bound(0, hp))} with zero failures",
         "actionability": f"{coded} of {len(fails)} failing cases carry a taxonomy v0.3 code ({pct(coded / len(fails))})",
         "efficiency": f"{always_pass} of {len(v11)} cases passed all four builds; leak scan found {leak['scan']['leaked_docs_found']} leaked documents with {leak['scan']['legit_docs_flagged']} false flags"}
for k, v in props.items():
    print(f"  {k:13s} {v}")
OUT["props"] = props; OUT["leak"] = leak
OUT["truss_version"] = truss.__version__
json.dump(OUT, open(HERE / "out/lab.json", "w"), indent=1, default=str)
print(f"\nTruss {truss.__version__}; seed 2026; wrote out/lab.json")
