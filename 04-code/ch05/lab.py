"""Chapter 5 Lab: code 150 Compass pilot traces, pool the notes, build taxonomy v0.1.
Run: python3 lab.py   (writes out/lab.json, out/taxonomy-v0.1.md, out/open_codes.csv)"""
import csv
import json
import random
from collections import Counter, defaultdict

import reading as R
import codebook as K
from truss import coding as C

con = R.store()
tr = R.truth()
out = {}

# ---------------------------------------------------------------- A. the draw
sample, hid_s, weights, info, rc = R.read_sample(con)
fp, hid_f = R.read_first_pass()
comp, hid_c, ctext = R.read_complaints(con)
hidden = {**hid_s, **hid_f, **hid_c}
print("A. Draw (Tue 15 Dec 2026)")
print(f"   frame {info['frame']:,} pilot traces after excluding {info['excluded']['union']} "
      f"(first-pass/gate {info['excluded']['first_pass']}, complaints {info['excluded']['complaints']})")
print(f"   re-contacted within 7 days, in frame: {info['recontact_in_frame']:,}")
byflow = Counter(c.flow for c in sample)
fails = Counter(c.flow for c in sample if c.verdict == "fail")
print("   flow               read  fail  cannot_tell  notes_on_passes")
for f in R.FLOWS:
    ct = sum(1 for c in sample if c.flow == f and c.verdict == "cannot_tell")
    npn = sum(1 for c in sample if c.flow == f and c.verdict == "pass" and c.note)
    print(f"   {f:18} {byflow[f]:4}  {fails[f]:4}  {ct:11}  {npn:15}")
nf = sum(fails.values())
w_read = [weights[c.trace_id] for c in sample]
rc_read = sum(1 for c in sample if c.trace_id in rc)
print(f"   total {len(sample)} read, {nf} failures ({nf / len(sample):.1%}); {rc_read} of 150 had a re-contact")
# what a uniform draw of the same quotas would have expected, from the store's planted rates
exp_uniform = 0
for f in R.FLOWS:
    ids = [t for t, fl in con.execute("SELECT trace_id, flow FROM traces") if fl == f]
    rate = sum(tr["fail"][t] for t in ids) / len(ids)
    exp_uniform += R.QUOTA[f] * rate
print(f"   a uniform draw within the same quotas expects {exp_uniform:.1f} failures")
out["draw"] = {"frame": info["frame"], "excluded": info["excluded"], "read": len(sample), "fails": nf,
               "by_flow": {f: [byflow[f], fails[f]] for f in R.FLOWS}, "recontact_read": rc_read,
               "uniform_expected": round(exp_uniform, 1)}

# ---------------------------------------------------------------- B. open coding
print("\nB. Open coding: one sentence per trace, before any category")
for oc in sample[:3] + [c for c in sample if c.verdict == "fail"][:4]:
    print(f"   #{oc.n:<3} {oc.trace_id} {oc.flow:18} {oc.verdict:11} {oc.note[:72]}")
pool = sample + fp + comp
failing = [c for c in pool if c.verdict == "fail"]
lint = {c.trace_id: C.note_problems(c.note) for c in failing}
bad = {t: p for t, p in lint.items() if p}
words = [len(c.note.split()) for c in failing]
print(f"   pooled failing notes: sample {sum(c.source == 'sample' for c in failing)}, first pass "
      f"{sum(c.source == 'first_pass' for c in failing)}, complaints {sum(c.source == 'complaint' for c in failing)} "
      f"= {len(failing)}")
print(f"   distinct wordings {len({c.note for c in failing})}; words per note median "
      f"{sorted(words)[len(words) // 2]}; notes the lint sends back {len(bad)}")
for t, p in list(bad.items())[:4]:
    print(f"     {t}: {p}")
vague = ["Wrong answer about the fee.", "Hallucinated.", "Bad hardship reply, confusing."]
print("   lint on three vague notes:", [C.note_problems(v) for v in vague])
mins = sum(c.minutes for c in sample) + sum(c.minutes for c in comp)
out["open"] = {"failing": len(failing), "by_source": dict(Counter(c.source for c in failing)),
               "distinct": len({c.note for c in failing}), "median_words": sorted(words)[len(words) // 2],
               "lint_back": len(bad), "lint_back_ids": bad, "minutes_reading": mins}

# ---------------------------------------------------------------- C. axial coding
print("\nC. Axial coding (Mon 21 Dec)")
idx = C.Index([c.note for c in failing], [c.trace_id for c in failing])
label = {c.trace_id: K.CODE_OF[hidden[c.trace_id]["cause"]] for c in failing}
sugg = {}
for th in (0.25, 0.35, 0.45, 0.55):
    g = C.suggest_groups(idx, th)
    sugg[th] = (len(g), round(C.purity(g, label), 3), sum(1 for x in g if len(x) == 1))
    print(f"   suggested groups at similarity {th}: {len(g):2} groups, purity {C.purity(g, label):.0%}, singletons {sugg[th][2]}")
draft, left_d = C.axial([c for c in pool], K.assigner(hidden, draft=True), K.categories(draft=True))
print(f"   draft clusters: {len(draft)}; unassigned failing notes {len(left_d)}")
cats, left = C.axial(pool, K.assigner(hidden), K.categories())
print(f"   after the payoff split: {len(cats)} categories; unassigned {len(left)}")
for d in K.DECISIONS:
    print(f"   {d[0]:5} {d[1]}: {d[2][:90]}")
print("   code   name                                                   S  FP   C  all")
tab = []
for c in cats:
    s = c.by_source(pool)
    tab.append([c.code, c.name, s.get("sample", 0), s.get("first_pass", 0), s.get("complaint", 0), len(c.members)])
    print(f"   {c.code}  {c.name[:52]:52} {s.get('sample', 0):2} {s.get('first_pass', 0):3} {s.get('complaint', 0):3} {len(c.members):4}")
person_sub = Counter(hidden[t]["sub"] or "first-pass wording" for t in K.categories() and
                     [m for c in cats if c.code == "FM-02" for m in c.members])
fee = {c.code: len(c.members) for c in cats if c.code in ("FM-05", "FM-06")}
fee_total = sum(fee.values())
top_share = max(fee.values()) / fee_total
print(f"   wrong-fee notes: {fee} -> FM-05 share {top_share:.0%}; two modes cover 100%")
by_src_modes = {s: sorted({c.code for c in cats for m in c.members if any(o.trace_id == m and o.source == s for o in pool)})
                for s in ("sample", "first_pass", "complaint")}
only = {s: sorted(set(v) - set().union(*[set(w) for k, w in by_src_modes.items() if k != s])) for s, v in by_src_modes.items()}
print("   modes seen per source:", {s: len(v) for s, v in by_src_modes.items()}, " only there:", only)
out["axial"] = {"suggest": {str(k): v for k, v in sugg.items()}, "draft_n": len(draft), "final_n": len(cats),
                "table": tab, "fee": fee, "fee_top_share": round(top_share, 3), "by_source": by_src_modes,
                "only": only, "person_sub": dict(person_sub)}
(R.OUT / "taxonomy-v0.1.md").write_text(C.codebook_markdown(cats, pool))
with open(R.OUT / "open_codes.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["n", "trace_id", "source", "flow", "verdict", "note", "annotator", "category"])
    for c in pool:
        w.writerow([c.n, c.trace_id, c.source, c.flow, c.verdict, c.note, c.annotator, c.category])

# ---------------------------------------------------------------- D. saturation
print("\nD. Saturation in the 150, reading order")
curve = C.saturation_curve(sample)
ln = C.last_new(curve)
print(f"   categories found in the 150: {curve[-1][2]}; last new category at trace {ln}; "
      f"{150 - ln} traces since without a new one")
marks = [(n, k) for n, f, k in curve if n in (25, 50, 75, 100, 125, 150)]
print("   (traces read, categories):", marks)
first_at = {}
for oc in sorted(sample, key=lambda c: c.n):
    if oc.verdict == "fail":
        first_at.setdefault(oc.category, oc.n)
print("   first appearance:", first_at)
floor = {}
print("   flow               read  rate seen at 95%   planted modes (frame rate, P(seen))")
for f in R.FLOWS:
    n = R.QUOTA[f]
    ids = [t for t, fl in con.execute("SELECT trace_id, flow FROM traces") if fl == f]
    cnt = Counter(tr["mode"][t] for t in ids if tr["fail"][t])
    modes = []
    for name, k in sorted(cnt.items(), key=lambda x: -x[1]):
        code = K.CODE_OF[R.CAUSE[name]]
        rate = k / len(ids)
        modes.append((code, round(rate, 4), round(C.detect_prob(rate, n), 2)))
    floor[f] = {"n": n, "floor": round(C.detectable_rate(n), 3), "modes": modes}
    print(f"   {f:18} {n:4}  {C.detectable_rate(n):6.1%}          " + "; ".join(f"{c} {r:.1%} {p:.0%}" for c, r, p in modes))
out["saturation"] = {"curve": curve, "last_new": ln, "first_at": first_at, "floor": floor}

# ---------------------------------------------------------------- E. one annotator or many
print("\nE. Hours (stated rates: you $85/h, loan officers $60/h, Ryan at $85/h)")
you_read = sum(c.minutes for c in sample) / 60
grace_pair = sum(c.minutes for c in sample if c.flow == R.H) / 60
comp_h = sum(c.minutes for c in comp) / 60
axial_h = 3.0
second = [c for c in failing]
ben_h = sum(R.MINUTES[c.flow] for c in second if c.flow == R.H) / 60
ryan_h = sum(R.MINUTES[c.flow] for c in second if c.flow != R.H) / 60
cost = {"you_read": you_read * 85, "grace_pair": grace_pair * 60, "complaints": comp_h * 85,
        "axial": axial_h * (85 + 60 + 85), "ben": ben_h * 60, "ryan": ryan_h * 85}
total = sum(cost.values())
for k, v in cost.items():
    print(f"   {k:11} ${v:8,.0f}")
print(f"   total      ${total:8,.0f}   (your reading hours {you_read:.1f}; Grace paired {grace_pair:.1f})")
panel = 3 * you_read * 85 + 3 * grace_pair * 60 + 4 * 85
print(f"   three readers on every trace instead: about ${panel:,.0f} for the reading alone, before reconciliation")
out["hours"] = {"you_read_h": round(you_read, 2), "grace_pair_h": round(grace_pair, 2), "complaints_h": round(comp_h, 2),
                "axial_h": axial_h, "ben_h": round(ben_h, 2), "ryan_h": round(ryan_h, 2),
                "cost": {k: round(v) for k, v in cost.items()}, "total": round(total), "panel_reading": round(panel)}

# ---------------------------------------------------------------- F. agreement (Tue 22 Dec)
print("\nF. Agreement: Ben (hardship) and Ryan (other flows) code every failing trace, notes hidden")
mine, theirs, kinds = [], [], Counter()
pairs = []
for c in failing:
    a = label[c.trace_id]
    r = random.Random(f"second|{c.trace_id}")
    b = a
    kind = None
    if a in ("FM-09", "FM-10") and r.random() < R.SWAP_PAYOFF:
        b, kind = ("FM-10" if a == "FM-09" else "FM-09"), "two categories fit"
    elif a == "FM-01" and r.random() < 0.25:
        b, kind = "pass", "is it a failure"
    elif a == "FM-07" and r.random() < 0.2:
        b, kind = "pass", "facts"
    mine.append(a); theirs.append(b)
    if kind:
        kinds[kind] += 1
        pairs.append((c.trace_id, c.source, a, b, kind))
k_all = C.cohen_kappa(mine, theirs)
agree = sum(x == y for x, y in zip(mine, theirs))
print(f"   agreement {agree}/{len(mine)}; kappa {k_all:.3f}")
for p in pairs:
    print("   ", p)
print("   kinds:", dict(kinds))
# after Grace's ruling on 'confirmed income' and Ryan re-reading the as-of dates
mine2 = mine[:]; theirs2 = [m if p and p in ("pass",) else t for m, t, p in zip(mine, theirs, theirs)]
theirs2 = [m if (t == "pass") else t for m, t in zip(mine, theirs)]
k_after = C.cohen_kappa(mine2, theirs2)
print(f"   after the income ruling and the facts re-read: kappa {k_after:.3f}; left: payoff swaps "
      f"{sum(1 for x, y in zip(mine2, theirs2) if x != y)}")
cats_only = [(x, y) for x, y in zip(mine, theirs)]
out["agreement"] = {"n": len(mine), "agree": agree, "kappa": round(k_all, 3), "pairs": pairs,
                    "kinds": dict(kinds), "kappa_after": round(k_after, 3),
                    "confusion": {f"{a}->{b}": n for (a, b), n in C.confusion(mine, theirs).items()},
                    "labels": sorted(set(mine) | set(theirs))}

# ---------------------------------------------------------------- G. hypotheses
print("\nG. From categories to hypotheses")
fee_read = [c for c in sample + comp if c.flow == R.F]
def schedule(t):
    rr = R.tools(con, t).get("retrieve") or {}
    return (rr.get("doc_versions") or [""])[0]
h1 = Counter((label.get(c.trace_id) == "FM-05", schedule(c.trace_id) == "fee-schedule-2024-01") for c in fee_read)
census = Counter(json.loads(a)["doc_versions"][0] for a, in con.execute(
    "SELECT s.attrs FROM spans s JOIN traces t USING(trace_id) WHERE s.kind='retrieve' AND t.flow='fee_explanation'"))
n_fee = con.execute("SELECT count(*) FROM traces WHERE flow='fee_explanation'").fetchone()[0]
print(f"   H1 FM-05 comes from retrieving the retired schedule. In the {len(fee_read)} December fee traces:")
print(f"      FM-05 & retired {h1[(True, True)]}, FM-05 & current {h1[(True, False)]}, "
      f"other & retired {h1[(False, True)]}, other & current {h1[(False, False)]}")
print(f"      census over all {n_fee:,} fee traces: retired schedule retrieved in {census['fee-schedule-2024-01']}")
hard = [c for c in sample if c.flow == R.H]
t_turns = dict(con.execute("SELECT trace_id, turns FROM traces"))
f1 = [t_turns[c.trace_id] for c in hard if label.get(c.trace_id) == "FM-01"]
p1 = [t_turns[c.trace_id] for c in hard if c.verdict == "pass"]
print(f"   H2 FM-01 follows from the pilot prompt, which never asked for income first: prompt read, "
      f"instruction absent; turns FM-01 {f1} vs passing median {sorted(p1)[len(p1) // 2]}; needs post-fix traces")
lien_read = [c for c in pool if c.flow == R.L and c.source != "first_pass"]
st = dict(con.execute("SELECT trace_id, state FROM traces"))
slow = {"NM", "CO"}
h3 = Counter((label.get(c.trace_id) == "FM-11", st[c.trace_id] in slow) for c in lien_read)
all_lien = Counter(s in slow for t, s in con.execute("SELECT trace_id, state FROM traces WHERE flow='lien_release'"))
print(f"   H3 FM-11 concentrates in slow title states (NM, CO). December lien traces {len(lien_read)}: "
      f"FM-11 slow {h3[(True, True)]} of {h3[(True, True)] + h3[(True, False)]}; other slow "
      f"{h3[(False, True)]} of {h3[(False, True)] + h3[(False, False)]}; all lien slow share "
      f"{all_lien[True] / sum(all_lien.values()):.0%}")
out["hypotheses"] = {"h1": {f"{k[0]}|{k[1]}": v for k, v in h1.items()}, "h1_census": census["fee-schedule-2024-01"],
                     "n_fee": n_fee, "h2_turns_fail": f1, "h2_turns_pass_median": sorted(p1)[len(p1) // 2],
                     "h3": {f"{k[0]}|{k[1]}": v for k, v in h3.items()},
                     "h3_slow_share_all": round(all_lien[True] / sum(all_lien.values()), 3), "n_lien_read": len(lien_read)}

# ---------------------------------------------------------------- H. trajectories
print("\nH. Trajectories: the first step that went wrong")
def after(tool):
    def rule(i, s, sp):
        if s["kind"] != "chat" or "router" in s["name"]:
            return False
        return any(x["kind"] == "execute_tool" and x["attrs"].get("tool_name") == tool for x in sp[:i])
    return rule
def tool(name):
    return lambda i, s, sp: s["kind"] == "execute_tool" and s["attrs"].get("tool_name") == name
def kind(k):
    return lambda i, s, sp: s["kind"] == k
def nth_reply(n):
    def rule(i, s, sp):
        replies = [j for j, x in enumerate(sp) if x["kind"] == "chat" and "router" not in x["name"]]
        return i == replies[min(n, len(replies) - 1)]
    return rule
RULES = {  # code -> (rule, origin type, visible from the replies alone?)
    "FM-01": (tool("draft_offer"), "action out of order", True),
    "FM-02": (nth_reply(2), "missing hand-off", True),
    "FM-03": (after("draft_offer"), "reply composition", True),
    "FM-04": (tool("draft_offer"), "action despite tool result", False),
    "FM-05": (kind("retrieve"), "retrieval", True),
    "FM-06": (after("get_fee_schedule"), "reading a tool result", False),
    "FM-07": (after("get_account"), "reading a tool result", False),
    "FM-08": (tool("get_account"), "tool arguments", False),
    "FM-09": (after("get_payoff_quote"), "reading a tool result", False),
    "FM-10": (after("get_payoff_quote"), "reading a tool result", False),
    "FM-11": (after("get_title_status"), "reading a tool result", False),
    "FM-12": (after("get_title_status"), "reading a tool result", False),
    "FM-13": (tool("send_statement"), "tool arguments", False),
}
traj = []
for c in [x for x in sample + comp if x.verdict == "fail"]:
    sp = R.spans(con, c.trace_id)
    code = label[c.trace_id]
    rule, origin, visible = RULES[code]
    i, s = C.first_wrong_step(sp, rule)
    final = max(j for j, x in enumerate(sp) if x["kind"] == "chat")
    traj.append({"trace_id": c.trace_id, "code": code, "spans": len(sp), "first": i, "kind": s["kind"] if s else None,
                 "origin": origin, "visible_in_replies": visible, "final_reply": final, "turns": t_turns[c.trace_id]})
orig = Counter(t["origin"] for t in traj)
vis = sum(t["visible_in_replies"] for t in traj)
early = sum(1 for t in traj if t["first"] < t["final_reply"])
pos = [t["first"] / t["spans"] for t in traj]
print(f"   December failing traces {len(traj)}: median spans {sorted(t['spans'] for t in traj)[len(traj) // 2]}")
print("   origin:", dict(orig))
print(f"   visible from replies alone {vis}/{len(traj)}; first wrong step before the last reply {early}/{len(traj)}; "
      f"median position {sorted(pos)[len(pos) // 2]:.0%} of the way through")
ex = [t for t in traj if t["code"] == "FM-04"][0]
print("   example FM-04:", ex)
out["trajectory"] = {"rows": traj, "origin": dict(orig), "visible": vis, "n": len(traj), "early": early,
                     "median_pos": round(sorted(pos)[len(pos) // 2], 3)}

# ---------------------------------------------------------------- I. searching by meaning
print("\nI. Searching notes by meaning (lexical stand-in for an embedding model)")
q_ids = [c.trace_id for c in failing if c.source != "first_pass"]
texts = [c.note for c in failing]
ids = [c.trace_id for c in failing]
res_v, res_j = {}, {}
for q in q_ids:
    qt = texts[ids.index(q)]
    res_v[q] = [i for i, _, _ in idx.search(qt, k=3, exclude=q)]
    res_j[q] = [i for i, _, _ in C.jaccard_search(texts, ids, qt, k=3, exclude=q)]
pv, pj = C.precision_at_k(res_v, label), C.precision_at_k(res_j, label)
print(f"   precision@3 over {len(q_ids)} December notes: vector {pv:.0%}, word overlap {pj:.0%}")
demo = []
for t, text in list(ctext.items())[:14]:
    hits = idx.search(text, k=3, exclude=t)
    demo.append((t, label[t], text, [(h[0], label[h[0]], h[1]) for h in hits]))
sizes = Counter(label.values())
fair = [d for d in demo if sizes[d[1]] > 1]
hit_rate = sum(1 for d in fair if any(h[1] == d[1] for h in d[3])) / len(fair)
print(f"   complaint texts as queries: a same-category note in the top 3 for {hit_rate:.0%} of {len(fair)} "
      f"(the FM-04 complaint has no other note to find)")
for d in demo[:3]:
    print(f"   {d[0]} [{d[1]}] '{d[2][:60]}' ->", [(h[1], h[2]) for h in d[3]])
out["search"] = {"p3_vector": round(pv, 3), "p3_jaccard": round(pj, 3), "n_queries": len(q_ids),
                 "complaint_hit": round(hit_rate, 3), "complaint_n": len(fair), "demo": demo}

# ---------------------------------------------------------------- J. release
print("\nJ. Taxonomy v0.1 released Wed 23 Dec 2026:", len(cats), "categories; codebook at out/taxonomy-v0.1.md")
out["release"] = {"date": "2026-12-23", "n": len(cats),
                  "codes": [[c.code, c.name, c.flows, c.layer, c.owner, c.severity, len(c.members)] for c in cats]}
out["samples"] = [[c.n, c.trace_id, c.flow, c.verdict, c.note, c.category] for c in sample]
out["pool"] = [[c.trace_id, c.source, c.flow, c.note, c.category, c.annotator] for c in failing]
json.dump(out, open(R.OUT / "lab.json", "w"), indent=1, default=list)
