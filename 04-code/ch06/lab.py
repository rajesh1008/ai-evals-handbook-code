"""Chapter 6 lab: re-code January under taxonomy v0.1, find what rotted, release v0.2, and
measure it on a holdout. Run: python3 lab.py  (writes out/lab.json, out/taxonomy-v0.2.json/.md)."""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
import truss
from truss import sampling as S
from truss import taxonomy as T
import january as J
import modes as M

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
R = {}

# pilot first pass (Chapter 2): failing traces per v0.1 mode, and traces read per flow
PILOT_READ = {"hardship": 100, "fee_explanation": 70, "account_question": 40, "payoff_letter": 35,
              "lien_release": 30, "statement_request": 25}
PILOT_FAIL = {"FM-01": 6, "FM-02": 3, "FM-03": 2, "FM-04": 0, "FM-05": 4, "FM-06": 2, "FM-07": 2,
              "FM-08": 1, "FM-09": 2, "FM-10": 1, "FM-11": 2, "FM-12": 1, "FM-13": 1}
PILOT_BACKCODE = {"t-019442": ("FM-02", "FM-14", "14:08, queue open, request repeated"),
                  "t-020266": ("FM-02", "FM-16", "17:29, request written in Spanish"),
                  "t-021059": ("FM-02", "FM-15", "19:45, queue closed, no callback"),
                  "t-015937": ("FM-13", "FM-17", "October asked for, September sent")}


def head(s):
    print(f"\n== {s}")


def risk_fn(frame):
    mean = defaultdict(list)
    for r in frame:
        mean[r["flow"]].append(r["turns"])
    mean = {f: sum(v) / len(v) for f, v in mean.items()}
    return lambda r: 1 + 3 * (r["risk_tier"] == "high") + r["turns"] / mean[r["flow"]] + r["handoff"]


def fits(code, r, tax):
    """Answer the mode's inclusion test from the trace's evidence."""
    if code is None:
        return False
    m = tax.modes[code]
    if not m.test:
        return True                       # no test written: any label 'fits' (v0.1 as it left Ch5)
    if code in ("FM-13", "FM-17"):
        return r.get("requested_doc") == "monthly" == r.get("sent_doc") and r["requested_period"] != r["sent_period"]
    if code == "FM-18":
        return r.get("requested_doc") == "year_end" and r.get("sent_doc") == "monthly"
    return r["cause"] in M.FITS.get(code, set())


def label(rows, tax, coder="first", rng=None):
    out = []
    for r in rows:
        if not r["cause"]:
            continue
        c = J.first_coder(r, tax.version) if coder == "first" else J.second_coder(r, tax.version, rng)
        if c and tax.modes[c].status not in ("active", "provisional"):
            c = None
        out.append({"trace_id": r["trace_id"], "flow": r["flow"], "cause": r["cause"], "code": c,
                    "fit": fits(c, r, tax), "note": r["note"]})
    return out


def cov_row(labels, read):
    c = T.coverage(labels)
    nm, nm_ci = T.new_mode_rate(labels, read)
    return {"failing": c["failing"], "coded": c["coded"], "fitted": c["fitted"],
            "naive": round(c["naive"], 3), "fitted_share": round(c["fitted_share"], 3),
            "fitted_ci": [round(x, 3) for x in c["fitted_ci"]],
            "none_fit": c["failing"] - c["fitted"], "new_mode_per_100": round(100 * nm, 1),
            "new_mode_ci": [round(100 * x, 1) for x in nm_ci]}


frame = J.build()
byid = {r["trace_id"]: r for r in frame}

# ---------------- A. draw the re-code sample and the holdout
head("A. samples")
early = [r for r in frame if r["day"] <= "2027-01-17"]
late = [r for r in frame if r["day"] >= "2027-01-18"]
risk = risk_fn(frame)
samp = S.risk_weighted(early, 400, risk, seed=J.SEED)
hold = S.risk_weighted(late, 200, risk, seed=J.SEED + 1)
man = S.manifest("jan-recode-2027-01", "risk_weighted", {"n": 400, "risk": "1+3*high+turns/mean+handoff"},
                 "started_at >= '2027-01-04' AND started_at < '2027-01-18' (Phoenix)",
                 [r["trace_id"] for r in early], samp, J.SEED, truss.__version__)
man_h = S.manifest("jan-holdout-2027-01", "risk_weighted", {"n": 200}, "started_at >= '2027-01-18' AND started_at < '2027-02-01'",
                   [r["trace_id"] for r in late], hold, J.SEED + 1, truss.__version__)
(OUT / "manifest-recode.json").write_text(S.dumps(man))
(OUT / "manifest-holdout.json").write_text(S.dumps(man_h))
srows = [byid[t] for t, _ in samp]
hrows = [byid[t] for t, _ in hold]
R["frame"] = {"traces": len(frame), "first": frame[0]["trace_id"], "last": frame[-1]["trace_id"],
              "early": len(early), "late": len(late), "per_day": round(len(frame) / 28)}
R["sample"] = {"n": len(srows), "flows": Counter(r["flow"] for r in srows), "failing": sum(1 for r in srows if r["cause"]),
               "frame_sha": man["frame_sha256"][:12]}
R["holdout"] = {"n": len(hrows), "flows": Counter(r["flow"] for r in hrows), "failing": sum(1 for r in hrows if r["cause"])}
print(f"frame {len(frame)} traces {frame[0]['trace_id']}..{frame[-1]['trace_id']}; early {len(early)}, late {len(late)}")
print(f"re-code sample {len(srows)} ({R['sample']['failing']} failing) {dict(R['sample']['flows'])}; frame sha {R['sample']['frame_sha']}")
print(f"holdout {len(hrows)} ({R['holdout']['failing']} failing) {dict(R['holdout']['flows'])}")

# ---------------- B. code January under v0.1 as it left error analysis, then the v0.1.1 patch
head("B. coding under v0.1 and the v0.1.1 patch")
t01 = M.v01()
R["v01_digest"] = t01.digest()
L01 = label(srows, t01)
R["v01_untested"] = cov_row(L01, len(srows))
t011 = M.v01()
rel011 = M.patch_011(t011)
L011 = label(srows, t011)
R["v011"] = cov_row(L011, len(srows))
changed = [(a["trace_id"], a["code"]) for a, b in zip(L01, L011) if a["fit"] != b["fit"]]
R["patch_changed"] = len(changed)
R["patch_changed_by_code"] = Counter(c for _, c in changed)
R["v011_digest"] = rel011["digest"]
print(f"v0.1 (no tests) digest {R['v01_digest']}: {R['v01_untested']}")
print(f"v0.1.1 patch {rel011['from']} -> {rel011['to']} ({len(rel011['changes'])} rewordings) digest {rel011['digest']}")
print(f"v0.1.1: {R['v011']}")
print(f"labels whose fit changed under a wording-only patch: {len(changed)} {dict(R['patch_changed_by_code'])}")
per_code = Counter(l["code"] for l in L011)
R["v01_codes"] = {c: per_code.get(c, 0) for c in t011.modes}
R["v01_codes"]["none"] = per_code.get(None, 0)
print("v0.1.1 labels per code:", R["v01_codes"])

# discovery curve: reading the sample in time order, cumulative failing traces with no fitting v0.1.1 mode,
# and distinct new causes among them (what an open-coding pass would name as new modes)
order = sorted(srows, key=lambda r: r["started_at"])
fitmap = {l["trace_id"]: l for l in L011}
seen, unfit, curve = set(), 0, []
for i, r in enumerate(order, 1):
    l = fitmap.get(r["trace_id"])
    if l and not l["fit"]:
        unfit += 1
        seen.add(r["cause"])
    curve.append((i, unfit, len(seen)))
R["discovery"] = curve
R["discovery_first"] = {}
for i, r in enumerate(order, 1):
    l = fitmap.get(r["trace_id"])
    if l and not l["fit"] and r["cause"] not in R["discovery_first"]:
        R["discovery_first"][r["cause"]] = i
print("discovery: new causes first seen at trace", R["discovery_first"])

# ---------------- C. drift: pilot first pass against January, per mode
head("C. drift against the pilot first pass")
read_jan = Counter(r["flow"] for r in srows)
before = {c: (PILOT_FAIL[c], PILOT_READ[t01.modes[c].flows[0]]) for c in t01.modes}
after = {c: (per_code.get(c, 0), read_jan[t01.modes[c].flows[0]]) for c in t01.modes}
dr = T.drift(before, after)
R["drift"] = [{"code": d["code"], "name": t01.modes[d["code"]].name, "before": d["before"], "after": d["after"],
               "p_up": round(d["p_up"], 4), "p_down": round(d["p_down"], 4), "flag": d["flag"]} for d in dr]
for d in R["drift"]:
    print(f"{d['code']} {d['before'][0]:>2}/{d['before'][1]:<3} -> {d['after'][0]:>2}/{d['after'][1]:<3} "
          f"p_up {d['p_up']:.4f} p_down {d['p_down']:.4f} {d['flag']}")

# ---------------- D. fit tests, note clusters, coder agreement
head("D. fit tests, note clusters, agreement")
R["clusters"] = {}
for code in ("FM-02", "FM-13", "FM-09", "FM-10", None):
    notes = [l["note"] for l in L011 if l["code"] == code]
    cl = T.clusters(notes)
    R["clusters"][str(code)] = [len(g) for g in cl]
    print(f"{code}: {len(notes)} notes -> clusters {[len(g) for g in cl]}")
    for g in cl:
        print("    e.g.", notes[g[0]])
R["fit_fail"] = {c: sum(1 for l in L011 if l["code"] == c and not l["fit"]) for c in t011.modes}
print("labels failing their mode's inclusion test:", {k: v for k, v in R["fit_fail"].items() if v})
rng = random.Random(J.SEED)
A1 = [l["code"] for l in L011]
B1 = [l["code"] for l in label(srows, t011, "second", rng)]
R["kappa_v01"] = round(T.kappa(A1, B1), 3)
pairs = Counter((a, b) for a, b in zip(A1, B1) if a != b)
R["disagree_v01"] = {f"{a}->{b}": n for (a, b), n in pairs.most_common()}
print(f"kappa on mode labels, v0.1.1: {R['kappa_v01']} over {len(A1)} failing traces; disagreements {R['disagree_v01']}")
rngp = random.Random(J.SEED + 7)
pay = [r for r in srows + hrows if r["cause"] in ("P_perdiem", "P_goodthru")]
pp = [(J.first_coder(r, "0.1.1"), J.second_coder(r, "0.1.1", rngp)) for r in pay]
R["payoff_pair_agree"] = [sum(a == b for a, b in pp), len(pp)]
print(f"payoff failures in re-code and holdout coded under v0.1.1 by both coders: agree {R['payoff_pair_agree'][0]} of {R['payoff_pair_agree'][1]}")

# ---------------- E. operations to v0.2
head("E. the v0.2 change set")
t02 = M.v01()
M.patch_011(t02)
M.v02_changes(t02)
ops = list(t02.log)

# ---------------- G (needed before release). incident-driven addition
head("G. incident: complaint 19 Jan 2027")
inc = [r for r in frame if r.get("complaint")][0]
R["incident"] = {"trace_id": inc["trace_id"], "started_at": inc["started_at"], "msg": inc["msg"]}
print(f"complaint 2027-01-19 about {inc['trace_id']} at {inc['started_at']}: '{inc['msg']}'")
KEYS = ("passed away", "died", "funeral", "estate", "co-signer passed")
pool = [r for r in frame if r["flow"] == "hardship" and r["day"] <= "2027-01-19" and r["trace_id"] != inc["trace_id"]]
cands = [r for r in pool if any(k in r["msg"] for k in KEYS)]
confirmed = [r for r in cands if r["cause"] == "H_bereave"]
seeded = [(r["trace_id"], None) for r in cands]
R["lookalike"] = {"searched": len(pool), "candidates": len(cands), "confirmed": len(confirmed),
                  "ids": [r["trace_id"] for r in confirmed], "weights": "none (incident-seeded, never pooled)"}
print(f"look-alike search over {len(pool)} hardship traces 4-19 Jan: {len(cands)} candidates, Grace confirms {len(confirmed)} {R['lookalike']['ids']}")
if confirmed:
    t02.promote("FM-21", f"confirmed in {len(confirmed)} more traces and a compliance event")
rel02 = t02.release("minor")
R["v02"] = {"version": rel02["to"], "digest": rel02["digest"], "changes": [(c["op"], c["codes"]) for c in rel02["changes"]
                                                                            if c["op"] != "reword"]}
R["v02_active"] = sorted(m.code for m in t02.active())
R["v02_status"] = Counter(m.status for m in t02.modes.values())
R["crosswalk"] = {k: v for k, v in t02.crosswalk().items() if v != [k]}
R["validate"] = t02.validate()
print(f"release {rel02['from']} -> {rel02['to']} digest {rel02['digest']}")
for c in R["v02"]["changes"]:
    print("   ", c)
print(f"active {len(R['v02_active'])}: {R['v02_active']}; status {dict(R['v02_status'])}")
print("crosswalk:", R["crosswalk"])
print("validate:", R["validate"] or "clean")
(OUT / "taxonomy-v0.2.json").write_text(t02.to_json())
md = [f"# Compass failure taxonomy v{t02.version} (digest {t02.digest()})", "",
      "| Code | Mode | Flow | Layer | Owner | Severity | Status | Inclusion test |", "|---|---|---|---|---|---|---|---|"]
for m in sorted(t02.modes.values(), key=lambda m: m.code):
    st = m.status + (f" -> {', '.join(m.replaced_by)}" if m.replaced_by else "")
    md.append(f"| {m.code} | {m.name} | {m.flows[0]} | L{m.layer} | {m.owner} | {m.severity} | {st} | {m.test} |")
(OUT / "taxonomy-v0.2.md").write_text("\n".join(md) + "\n")
R["backcode"] = PILOT_BACKCODE
print("pilot back-coding (splits need a re-read; merges map automatically):")
for t, (a, b, why) in PILOT_BACKCODE.items():
    print(f"   {t} {a} -> {b}  ({why})")

# ---------------- F. re-score the same traces under v0.2
head("F. same traces under v0.2")
L02 = label(srows, t02)
R["v02_recode"] = cov_row(L02, len(srows))
rng = random.Random(J.SEED)
A2 = [l["code"] for l in L02]
B2 = [l["code"] for l in label(srows, t02, "second", rng)]
R["kappa_v02"] = round(T.kappa(A2, B2), 3)
print(f"v0.2 on re-code sample: {R['v02_recode']}")
print(f"kappa on mode labels, v0.2: {R['kappa_v02']} (v0.1.1 {R['kappa_v01']})")
print("note: coverage of v0.2 on the sample it was built from is circular; the holdout is the measure")

# ---------------- H. holdout coverage, check coverage, retirement bound
head("H. holdout and check coverage")
LH = label(hrows, t02)
R["v02_holdout"] = cov_row(LH, len(hrows))
R["holdout_unfit"] = Counter(l["cause"] for l in LH if not l["fit"])
R["recode_unfit_v02"] = [(l["trace_id"], l["cause"], l["note"]) for l in L02 if not l["fit"]]
print("v0.2 open codes on re-code sample (no mode fits):", R["recode_unfit_v02"])
LH01 = label(hrows, t011)
R["v011_holdout"] = cov_row(LH01, len(hrows))
print(f"v0.1.1 on holdout: {R['v011_holdout']}")
print(f"v0.2 on holdout: {R['v02_holdout']}; unfit causes {dict(R['holdout_unfit'])}")
CHECKS = {"FM-01": [3], "FM-02": [3], "FM-03": [3], "FM-04": [1, 3], "FM-05": [1], "FM-06": [1, 3],
          "FM-07": [3], "FM-08": [3], "FM-09": [3], "FM-10": [3], "FM-11": [3], "FM-12": [3], "FM-13": [3],
          "FM-14": [3], "FM-15": [3], "FM-16": [3], "FM-17": [3], "FM-18": [3], "FM-19": [3],
          "FM-20": [3], "FM-21": [3]}
w01 = Counter(l["code"] for l in L011 if l["fit"])
w02 = Counter(l["code"] for l in L02 if l["fit"])
cc01 = T.check_coverage(t011, CHECKS, w01)
cc02 = T.check_coverage(t02, CHECKS, w02)
R["check_cov"] = {"v011": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cc01.items()},
                  "v02": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cc02.items()}}
print(f"check coverage v0.1.1: {cc01['with_check']}/{cc01['modes']} = {cc01['share']:.0%}, failure-weighted {cc01['weighted_share']:.0%}; missing {cc01['missing']}")
print(f"check coverage v0.2:   {cc02['with_check']}/{cc02['modes']} = {cc02['share']:.0%}, failure-weighted {cc02['weighted_share']:.0%}; missing {cc02['missing']}")
fee_read = sum(1 for r in srows + hrows if r["flow"] == "fee_explanation")
R["retire"] = {"fee_read_since_removal": fee_read, "bound": round(T.zero_bound(fee_read), 3),
               "bound_20": round(T.zero_bound(20), 3), "needed_2pct": T.clean_traces_to_retire(.02),
               "needed_1pct": T.clean_traces_to_retire(.01)}
print(f"FM-05: 0 in {fee_read} fee traces read since 16 Dec -> bound {R['retire']['bound']:.1%}; "
      f"0 in 20 -> {R['retire']['bound_20']:.1%}; clean traces for a 2% bound {R['retire']['needed_2pct']}, 1% {R['retire']['needed_1pct']}")
R["per_code_v02"] = dict(Counter(l["code"] for l in L02))
R["per_code_hold"] = dict(Counter(l["code"] for l in LH))
print("v0.2 labels per code (re-code):", R["per_code_v02"])
print("v0.2 labels per code (holdout):", R["per_code_hold"])
def cost(rows):
    h = sum(1 for r in rows if r["flow"] == "hardship")
    return {"hardship": h, "other": len(rows) - h, "officer_hours": round(h * 10 / 60, 1),
            "lead_hours": round((len(rows) - h) * 3 / 60, 1), "dollars": round(h * 10 / 60 * 60 + (len(rows) - h) * 3 / 60 * 85)}
fail_rows = [r for r in srows if r["cause"]]
R["cost"] = {"recode": cost(srows), "second_coding": cost(fail_rows), "holdout": cost(hrows),
             "lookalike": {"traces": len(cands), "dollars": round(len(cands) * 10)}}
print("reading cost ($60/h officers, 10 min a hardship trace; $85/h lead, 3 min otherwise):", R["cost"])
R["truss_version"] = truss.__version__
(OUT / "lab.json").write_text(json.dumps(R, indent=1, default=list))
print("\nwrote out/lab.json, out/taxonomy-v0.2.json, out/taxonomy-v0.2.md, manifests")
