"""Chapter 14 lab: five weeks of the annotation operation (9 August to 10 September 2027), the selection
study on the REAL pre-labels, the SIMULATED automation-bias study, cost designs and the debt register.
Annotator behaviour is SIMULATED (annotators.py); the pre-labels are a REAL model run (prelabel.py)."""
import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "truss"))
import annotators as A
import fixture as F
import guideline as G
from truss import annotation as AN
from truss.adjudication import kappa
from truss.rates import wilson

L = list(F.LABELS)
WEEK_NAMES = ["9-13 Aug", "16-20 Aug", "23-27 Aug", "30 Aug-3 Sep", "7-10 Sep"]
ANCHORS = F.gold_cases(30, 7, "a")
QUAL = F.gold_cases(40, 11, "q")


def schedule(inject=False):
    later = "ops-1.1-minus-anniversary" if inject else "ops-1.1"
    return ["ops-1.0"] + [later] * 4


def run(inject=False, seed=2026, verbose=False):
    W = F.build()
    vers = schedule(inject)
    weeks = []
    for w in range(1, 6):
        g = random.Random(seed * 10 + w)
        frame = W[w - 1]
        draw = sorted(random.Random(500 + w).sample(frame, 60), key=lambda t: t["trace_id"])
        anchors = ANCHORS[(w - 1) * 6: w * 6]
        by_id = {t["trace_id"]: t for t in draw + anchors}
        readers = A.READERS if w != 5 else ("marisol", "kevin")
        must = (lambda tid: "marisol" if by_id[tid]["facts"]["lang"] == "es" else None) if w >= 3 else None
        jobs = AN.assign([t["trace_id"] for t in draw], readers, triple=0.2 if w != 5 else 0.0,
                         anchors=[a["trace_id"] for a in anchors], seed=seed + w, must_include=must)
        cap = 45 if w >= 3 else {"marisol": 90, "daniel": 90, "kevin": 60}
        ver = vers[w - 1]
        since = 0 if w == 2 else (w - 2)
        readings, why, mins, sitting = defaultdict(dict), defaultdict(dict), defaultdict(float), defaultdict(float)
        late, late_of = Counter(), defaultdict(dict)
        for _, tid, r in jobs:
            t = by_id[tid]
            c = cap if isinstance(cap, int) else cap[r]
            if sitting[r] >= c:
                sitting[r] = 0.0
            lab, y = A.read(r, t, ver, w, since, sitting[r], g)
            m = A.minutes(r, t, w, g)
            late[r] += sitting[r] > 45
            late_of[tid][r] = sitting[r] > 45
            sitting[r] += m
            readings[tid][r], why[tid][r] = lab, y
            mins[r] += m
        live = {k: v for k, v in readings.items() if not k.startswith("a-")}
        # adjudication of every disagreement on live traces
        disagree = sorted(t for t, v in live.items() if len(set(v.values())) > 1)
        limit = 2 if w == 5 else None              # week 5: Ben had twenty minutes for rulings
        ruled, kinds, adj_min = {}, Counter(), 0.0
        for i, tid in enumerate(disagree):
            if limit is not None and i >= limit:
                break
            t = by_id[tid]
            ruled[tid] = t["required"] if g.random() < 0.98 else g.choice(L[:5])
            ys = set(why[tid].values())
            kinds["fact" if t["required"] == "cannot_tell" else "guideline" if "habit" in ys
                  else "slip" if "slip" in ys else "guideline"] += 1
            adj_min += 6.0 * pow(2.718, g.gauss(0, 0.3))
        final, pending = AN.final_labels(live, ruled)
        agreed = [t for t in live if len(set(live[t].values())) == 1]
        audit = AN.audit_draw(agreed, 0.1, seed + w)
        audit_wrong = [t for t in audit if final[t] != by_id[t]["required"]]
        for t in audit_wrong:
            final[t] = by_id[t]["required"]
        adj_min += 3.0 * len(audit)
        wk = {"week": w, "dates": WEEK_NAMES[w - 1], "version": ver, "readers": list(readers), "n": len(draw),
              "reads": len(jobs), "readings": {k: dict(v) for k, v in readings.items()}, "why": {k: dict(v) for k, v in why.items()},
              "minutes": dict(mins), "late_reads": dict(late), "late_of": {k: dict(v) for k, v in late_of.items()}, "disagree": disagree, "ruled": ruled, "kinds": dict(kinds),
              "pending": pending, "audit": audit, "audit_wrong": audit_wrong, "adj_minutes": adj_min, "final": final,
              "required": {k: by_id[k]["required"] for k in by_id}, "lang": {k: by_id[k]["facts"]["lang"] for k in by_id},
              "anniv": [k for k in live if F.is_anniversary(by_id[k]["facts"])],
              "stated": [k for k in live if F.is_stated_work(by_id[k]["facts"])],
              "touch_window_or_work": [k for k in live if by_id[k]["facts"]["relief"] or F.is_stated_work(by_id[k]["facts"])],
              "compass": {k: by_id[k]["compass"] for k in by_id}}
        weeks.append(wk)
    return weeks


def stats(weeks):
    out = []
    for wk in weeks:
        live = {k: v for k, v in wk["readings"].items() if not k.startswith("a-")}
        pw = AN.pairwise(live, wk["readers"])
        trip = [list(v.values()) for v in live.values() if len(v) == 3]
        anc = AN.anchor_table({k: v for k, v in wk["readings"].items() if k.startswith("a-")},
                              {k: v for k, v in wk["required"].items() if k.startswith("a-")}, wk["readers"])
        acc = sum(wk["final"][t] == wk["required"][t] for t in wk["final"])
        out.append({"week": wk["week"], "dates": wk["dates"], "version": wk["version"],
                    "pairs": {f"{a}-{b}": {"n": v["n"], "agree": v["agree"], "kappa": round(v["kappa"], 3)} for (a, b), v in pw.items()},
                    "fleiss": round(AN.fleiss_kappa(trip, L), 3) if trip else None, "n_triple": len(trip),
                    "anchors": {r: [v["right"], v["n"]] for r, v in anc.items()},
                    "disagree": len(wk["disagree"]), "kinds": wk["kinds"], "pending": len(wk["pending"]),
                    "audit": len(wk["audit"]), "audit_wrong": len(wk["audit_wrong"]),
                    "final_right": acc, "final_n": len(wk["final"]),
                    "minutes": {r: round(m, 1) for r, m in wk["minutes"].items()}, "adj_minutes": round(wk["adj_minutes"], 1),
                    "late_reads": wk["late_reads"]})
    return out


def pooled_kappa(weeks, a, b, wks):
    la, lb = [], []
    for wk in weeks:
        if wk["week"] in wks:
            for k, v in wk["readings"].items():
                if not k.startswith("a-") and a in v and b in v:
                    la.append(v[a]); lb.append(v[b])
    return kappa(la, lb), len(la)


def pooled_matrix(weeks, a, b, wks):
    la, lb = [], []
    for wk in weeks:
        if wk["week"] in wks:
            for k, v in wk["readings"].items():
                if not k.startswith("a-") and a in v and b in v:
                    la.append(v[a]); lb.append(v[b])
    from truss.adjudication import matrix
    return matrix(la, lb, L)


def cell(m, x, y):
    i, j = L.index(x), L.index(y)
    return m[i][j] + m[j][i]


def qualification():
    g = random.Random(55)
    res = {}
    for r in A.READERS:
        right = 0
        for t in QUAL:
            lab, _ = A.read(r, t, "ops-1.0", 1, 0, 0, g)
            right += lab == t["required"]
        res[r] = right
    return res


def anniversary_week1(weeks):
    wk = weeks[0]
    rows = []
    for t in wk["anniv"]:
        rows.append({"trace": t, "readings": wk["readings"][t], "required": wk["required"][t], "final": wk["final"][t]})
    return rows


def costs(weeks, st_rows):
    rows = []
    for wk, s in zip(weeks, st_rows):
        live_n = wk["n"]
        session = 0.5 * (len(wk["readers"]) * 1 + 1) * 60 + 0.5 * A.RATE["diane"]
        extra = [("adjudication and audit", wk["adj_minutes"] / 60 * A.RATE["adjudicator"]), ("alignment session", session)]
        c = AN.cost_per_label(wk["minutes"], A.RATE, live_n, extra)
        anchor_min = 0
        rows.append({"week": wk["week"], "per_label": round(c["per_label"], 2), "total": round(c["total"], 2),
                     "parts": [(p, round(v, 2)) for p, v in c["parts"]],
                     "reader_hours": round(sum(wk["minutes"].values()) / 60, 2),
                     "adj_hours": round(wk["adj_minutes"] / 60, 2)})
    return rows


def designs(weeks):
    """Accuracy and cost of four designs on the same readings of weeks 2-5 (reading minutes estimated
    from each reader's mean minutes that week)."""
    out = {}
    g = random.Random(9)
    res = defaultdict(lambda: [0, 0, 0.0])
    for wk in weeks[1:]:
        mean_min = {r: wk["minutes"][r] / sum(1 for v in wk["readings"].values() for x in v if x == r) for r in wk["readers"]}
        live = {k: v for k, v in wk["readings"].items() if not k.startswith("a-")}
        for i, (t, v) in enumerate(sorted(live.items())):
            req = wk["required"][t]
            rs = sorted(v)
            first = rs[i % len(rs)]
            # single read
            res["single read"][0] += v[first] == req; res["single read"][1] += 1
            res["single read"][2] += mean_min[first] * A.RATE[first] / 60
            # single read with 20% double read and adjudication on the overlap
            if i % 5 == 0:
                two = rs[:2]
                lab = v[two[0]] if v[two[0]] == v[two[1]] else wk["ruled"].get(t, req)
                res["single + 20% double"][0] += lab == req
                res["single + 20% double"][2] += sum(mean_min[r] * A.RATE[r] / 60 for r in two) + (0.1 * A.RATE["adjudicator"] if v[two[0]] != v[two[1]] else 0)
            else:
                res["single + 20% double"][0] += v[first] == req
                res["single + 20% double"][2] += mean_min[first] * A.RATE[first] / 60
            res["single + 20% double"][1] += 1
            # double read with adjudication (no audit)
            two = rs[:2]
            agree = v[two[0]] == v[two[1]]
            lab = v[two[0]] if agree else wk["ruled"].get(t, req)
            res["double + adjudication"][0] += lab == req; res["double + adjudication"][1] += 1
            res["double + adjudication"][2] += sum(mean_min[r] * A.RATE[r] / 60 for r in two) + (0 if agree else 0.1 * A.RATE["adjudicator"])
        # as run (with audit and triple reads)
        res["as run (double, 20% triple, audit)"][0] += sum(wk["final"][t] == wk["required"][t] for t in wk["final"])
        res["as run (double, 20% triple, audit)"][1] += len(wk["final"])
        res["as run (double, 20% triple, audit)"][2] += sum(m * A.RATE[r] / 60 for r, m in wk["minutes"].items()) + wk["adj_minutes"] / 60 * A.RATE["adjudicator"]
    for k, (right, n, cost) in res.items():
        out[k] = {"right": right, "n": n, "accuracy": round(right / n, 4), "dollars_per_label": round(cost / n, 2)}
    return out


def debt_register(weeks, upto):
    """The register on the Friday of week `upto` (and on Mon 13 Sep for upto=5)."""
    reg = []
    w1 = weeks[0]
    if upto >= 1:
        reread = [t for t in w1["touch_window_or_work"] if len(set(w1["readings"][t].values())) == 1 and "kevin" not in w1["readings"][t]]
        done = 0 if upto < 3 else len(reread) // 2   # half re-read in week 3; none in the short week 5
        reg.append({"kind": "re-read after guideline change", "items": len(reread) - done, "minutes_each": 4, "blocks": True,
                    "owner": "Marisol and Kevin", "note": "week-one labels on window or work traces read by the two officers only"})
    reg.append({"kind": "authored awaiting review", "items": 40 if upto < 4 else 26, "minutes_each": 8, "blocks": False,
                "owner": "Grace or Ben", "note": "the officers' 40 adversarial cases from Chapter 12; never in a rate"})
    pend = sum(len(wk["pending"]) for wk in weeks[:upto])
    reg.append({"kind": "unadjudicated", "items": pend, "minutes_each": 6, "blocks": True, "owner": "Ben", "note": "rulings owed"})
    ct = sum(1 for wk in weeks[:upto] for t, l in wk["final"].items() if l == "cannot_tell")
    reg.append({"kind": "cannot tell open", "items": ct, "minutes_each": 10, "blocks": True, "owner": "Kevin with the trace owner",
                "note": "missing relief end date; the servicing record has to be fetched"})
    reg.append({"kind": "audit due", "items": 30 if upto >= 4 else 0, "minutes_each": 4, "blocks": False, "owner": "Grace",
                "note": "monthly re-read of 30 labels from four weeks ago"})
    return reg


# -------------------------------------------------------------------- selection study (REAL pre-labels)
def selection():
    import prelabel as P
    pre = P.load()
    W = F.build()
    frame = {t["trace_id"]: t for t in W[0] + W[1]}
    ids = sorted(frame)
    fail = {t: int(frame[t]["required"] != "cannot_tell" and frame[t]["compass"] != frame[t]["required"]) for t in ids}
    maj = {t: Counter(a for a, _ in pre[t]).most_common(1)[0][0] for t in ids}
    n_distinct = {t: len(set(a for a, _ in pre[t])) for t in ids}
    meanconf = {t: st.mean(c for _, c in pre[t] if isinstance(c, (int, float))) for t in ids}
    unc = lambda t: (n_distinct[t] - 1) + (100 - meanconf[t]) / 100
    sus = lambda t: (maj[t] != frame[t]["compass"]) + unc(t) / 10
    g = random.Random(4)
    mins = {t: 3.7 * (1.2 if (frame[t]["facts"]["relief"] or frame[t]["facts"]["loans"] > 1) else 1.0) *
            (1.1 if frame[t]["facts"]["lang"] == "es" else 1.0) for t in ids}
    hours = lambda pick: sum(mins[t] for t in pick) * 2 / 60     # two readers on every trace read
    def kind(t):
        f = frame[t]["facts"]
        return ("anniversary (FM-20)" if F.is_anniversary(f) else "stated work" if F.is_stated_work(f) else
                "take-home income" if f["income_basis"] == "take_home" and frame[t]["compass"] == "ask_income" else
                "unclear loan" if f["loan_unclear"] else "other")
    res = {"frame": len(ids), "failures": sum(fail.values()), "true_rate": sum(fail.values()) / len(ids),
           "by_kind": dict(Counter(kind(t) for t in ids if fail[t]))}
    reps = []
    for s in range(1000):
        pick, inc = AN.select(ids, 60, "random", seed=s)
        reps.append((sum(fail[t] for t in pick), hours(pick)))
    res["random"] = {"found_mean": st.mean(r[0] for r in reps), "found_p5": sorted(r[0] for r in reps)[50],
                     "found_p95": sorted(r[0] for r in reps)[949], "hours": st.mean(r[1] for r in reps)}
    flagged = [t for t in ids if maj[t] != frame[t]["compass"]]
    for name, kw in [("uncertainty", {"score": unc}), ("failure", {"pool": flagged})]:
        pick, inc = AN.select(ids, 60, name, seed=3, **kw)
        res[name] = {"found": sum(fail[t] for t in pick), "hours": hours(pick),
                     "naive_rate": sum(fail[t] for t in pick) / 60,
                     "kinds": dict(Counter(kind(t) for t in pick if fail[t]))}
        try:
            AN.ht_rate(fail, inc, len(ids))
        except ValueError as e:
            res[name]["rate"] = f"refused: {e}"
    fr_reps = []
    for s in range(1000):
        pick, _ = AN.select(ids, 60, "failure", seed=s, pool=flagged)
        fr_reps.append(sum(fail[t] for t in pick))
    res["failure"]["found_mean"] = st.mean(fr_reps)
    res["failure"]["found_p5"], res["failure"]["found_p95"] = sorted(fr_reps)[50], sorted(fr_reps)[949]
    res["read_all_flagged"] = {"n": len(flagged), "found": sum(fail[t] for t in flagged), "hours": hours(flagged)}
    mixed = []
    for s in range(1000):
        pick, inc = AN.select(ids, 60, "mixed", seed=s, mix_targeted=15, pool=flagged)
        mixed.append((sum(fail[t] for t in pick), hours(pick), AN.ht_rate(fail, inc, len(ids))))
    res["mixed"] = {"found_mean": st.mean(m[0] for m in mixed), "hours": st.mean(m[1] for m in mixed),
                    "ht_rate_mean": st.mean(m[2] for m in mixed), "ht_rate_sd": st.pstdev(m[2] for m in mixed)}
    rr = [r[0] / 60 for r in reps]
    res["random"]["rate_mean"], res["random"]["rate_sd"] = st.mean(rr), st.pstdev(rr)
    res["suspect_count"] = sum(maj[t] != frame[t]["compass"] for t in ids)
    res["suspect_true_fail"] = sum(fail[t] for t in flagged)
    missed = [t for t in ids if fail[t] and maj[t] == frame[t]["compass"]]
    res["missed_by_prelabel"] = {"n": len(missed), "kinds": dict(Counter(kind(t) for t in missed))}
    # pre-labeller quality
    unan = [t for t in ids if n_distinct[t] == 1]
    res["prelabel"] = {"majority_right": sum(maj[t] == frame[t]["required"] for t in ids),
                       "unanimous": len(unan), "unanimous_right": sum(maj[t] == frame[t]["required"] for t in unan),
                       "split": len(ids) - len(unan), "split_right": sum(maj[t] == frame[t]["required"] for t in ids if t not in unan),
                       "conf_values": dict(Counter(c for t in ids for _, c in pre[t])),
                       "by_required": {}}
    for lab in L:
        xs = [t for t in ids if frame[t]["required"] == lab]
        if xs:
            res["prelabel"]["by_required"][lab] = [sum(maj[t] == lab for t in xs), len(xs)]
    byc = defaultdict(lambda: [0, 0])
    for t in ids:
        c = round(meanconf[t])
        b = "95" if c >= 95 else "90-94" if c >= 90 else "<90"
        byc[b][1] += 1; byc[b][0] += maj[t] == frame[t]["required"]
    res["prelabel"]["by_conf"] = dict(byc)
    for nm, fn in [("anniversary", F.is_anniversary), ("stated work", F.is_stated_work)]:
        xs = [t for t in ids if fn(frame[t]["facts"])]
        res["prelabel"][nm] = [sum(maj[t] == frame[t]["required"] for t in xs), len(xs)]
    xs = [t for t in ids if frame[t]["facts"]["lang"] == "es"]
    res["prelabel"]["spanish"] = [sum(maj[t] == frame[t]["required"] for t in xs), len(xs)]
    return res, maj


# -------------------------------------------------------------------- automation bias (SIMULATED readers, REAL suggestions)
def automation_bias(maj, p_wrong=0.07, p_right=0.6, seed=31):
    W = F.build()
    frame = W[0] + W[1]
    out = {}
    for cond in ("blind", "Compass reply shown", "pre-label shown"):
        g = random.Random(seed)
        la, lb, req, both_wrong, hidden = [], [], [], 0, 0
        for t in frame:
            labs = []
            for r in ("marisol", "daniel"):
                own, _ = A.read(r, t, "ops-1.1", 3, 1, 0, g)
                s = {"blind": None, "Compass reply shown": t["compass"], "pre-label shown": maj[t["trace_id"]]}[cond]
                u = g.random()
                if s is not None and own != s:
                    if own == t["required"] and u < p_wrong:
                        own = s
                    elif own != t["required"] and s == t["required"] and u < p_right:
                        own = s
                labs.append(own)
            la.append(labs[0]); lb.append(labs[1]); req.append(t["required"])
            both_wrong += labs[0] == labs[1] != t["required"]
            hidden += labs[0] == labs[1] == t["compass"] != t["required"]
        out[cond] = {"kappa": round(kappa(la, lb), 3), "agree": sum(a == b for a, b in zip(la, lb)),
                     "acc": round(st.mean([(a == r) for a, r in zip(la, req)] + [(b == r) for b, r in zip(lb, req)]), 4),
                     "agreed_wrong": both_wrong, "hidden_compass_failures": hidden,
                     "compass_failures": sum(t["compass"] != t["required"] and t["required"] != "cannot_tell" for t in frame), "n": len(frame)}
    return out


def main():
    weeks = run()
    S = stats(weeks)
    print("== Qualification, Thu 5 Aug 2027 (40 cases from hardship-gold, ops-1.0) SIMULATED")
    q = qualification()
    print("   pass mark 34/40 (85%), set before the test;", ", ".join(f"{r} {v}/40" for r, v in q.items()))
    print("== Weekly agreement, SIMULATED readers (60 random hardship traces a week)")
    for s in S:
        prs = "; ".join(f"{k} {v['kappa']:.2f} (n {v['n']})" for k, v in s["pairs"].items())
        anc = ", ".join(f"{r} {a}/{n}" for r, (a, n) in s["anchors"].items())
        print(f"  week {s['week']} {s['dates']} [{s['version']}] {prs}; Fleiss {s['fleiss']} on {s['n_triple']}; "
              f"anchors {anc}; disagreements {s['disagree']} {s['kinds']}; pending {s['pending']}; "
              f"audit {s['audit_wrong']}/{s['audit']} wrong; final right {s['final_right']}/{s['final_n']}")
    k_md, n_md = pooled_kappa(weeks, "marisol", "daniel", {2, 3, 4})
    k_md5, n_md5 = pooled_kappa(weeks, "marisol", "daniel", {2, 3, 4, 5})
    k1, n1 = pooled_kappa(weeks, "marisol", "daniel", {1})
    print(f"  Marisol-Daniel kappa: week 1 {k1:.3f} (n {n1}); weeks 2-4 pooled {k_md:.3f} (n {n_md}); Daniel absent in week 5")
    for a, b in [("marisol", "kevin"), ("daniel", "kevin")]:
        k, n = pooled_kappa(weeks, a, b, {2, 3, 4, 5})
        print(f"  {a}-{b} weeks 2-5 pooled {k:.3f} (n {n})")
    print("== Anniversary traces in week 1 (ops-1.0 is silent)")
    for r in anniversary_week1(weeks):
        print("  ", r)
    m1 = pooled_matrix(weeks, "daniel", "kevin", {1}); m1b = pooled_matrix(weeks, "marisol", "kevin", {1})
    m1o = pooled_matrix(weeks, "marisol", "daniel", {1})
    print(f"  week 1 cell window x draft: officer-Kevin pairs {cell(m1, 'decline_window', 'draft_deferral') + cell(m1b, 'decline_window', 'draft_deferral')}, "
          f"officer pair {cell(m1o, 'decline_window', 'draft_deferral')}")
    print(f"  week 1 cell refer x draft: officer-Kevin pairs {cell(m1, 'refer_to_officer', 'draft_deferral') + cell(m1b, 'refer_to_officer', 'draft_deferral')}, "
          f"officer pair {cell(m1o, 'refer_to_officer', 'draft_deferral')}")
    w1 = weeks[0]
    hab = [t for t in w1["disagree"] if "habit" in w1["why"][t].values()]
    withk = sum("kevin" in w1["readings"][t] for t in hab)
    sh = sum(1 for k, v in w1["readings"].items() if not k.startswith("a-") and "kevin" in v and len(v) >= 2)
    dk = sum(1 for k, v in w1["readings"].items() if not k.startswith("a-") and "kevin" in v
             and any(v[r] != v["kevin"] for r in v if r != "kevin"))
    print(f"  week 1 disagreements from a reading habit: {len(hab)}, of which with Kevin in the pair {withk}; "
          f"traces Kevin shared with an officer {sh}, with a different label {dk}")
    print("== Sittings: reads after minute 45 by week", [s["late_reads"] for s in S])
    sp = [(wk["week"], sum(1 for t, v in wk["readings"].items() if wk["lang"].get(t) == "es" and "daniel" in v and v["daniel"] != wk["required"][t]),
           sum(1 for t, v in wk["readings"].items() if wk["lang"].get(t) == "es" and "daniel" in v)) for wk in weeks]
    print("  Daniel on Spanish traces, wrong/read by week", sp)
    sl = []
    for wk in weeks:
        a = sum(1 for t, v in wk["why"].items() for r, y in v.items() if y == "slip" and wk["late_of"][t][r])
        b = sum(1 for t, v in wk["why"].items() for r, y in v.items() if y == "slip")
        n_late = sum(1 for t, v in wk["late_of"].items() for r, x in v.items() if x)
        n_all = sum(len(v) for v in wk["late_of"].values())
        sl.append((wk["week"], a, b, n_late, n_all))
    print("  slips after minute 45 / all slips, late reads / all reads, by week", sl)
    C = costs(weeks, S)
    print("== Cost per final label (readers $60/h officers, $85/h Kevin; adjudication $60/h; session 30 minutes)")
    for c in C:
        print(f"  week {c['week']}: ${c['per_label']:.2f} a label, ${c['total']:.0f} total; reader hours {c['reader_hours']}, adjudicator hours {c['adj_hours']}")
    D = designs(weeks)
    print("== Designs on weeks 2-5 readings")
    for k, v in D.items():
        print(f"  {k}: {v['right']}/{v['n']} right ({v['accuracy']:.1%}), ${v['dollars_per_label']:.2f} a label")
    print("== Debt register")
    debts = []
    for w in range(1, 6):
        reg = debt_register(weeks, w)
        d = AN.debt(reg)
        debts.append({"week": w, "hours": d["hours"], "total": round(d["total_hours"], 2), "blocking": d["blocking_items"]})
        print(f"  end of week {w}: {round(d['total_hours'], 1)} h, blocking items {d['blocking_items']}  {({k: round(v, 1) for k, v in d['hours'].items()})}")
    reg13 = debt_register(weeks, 5)
    for r in reg13:
        print(f"    {r['kind']}: {r['items']} x {r['minutes_each']} min, owner {r['owner']}, blocks a rate {r['blocks']}; {r['note']}")
    print("== Failure injection: ops-1.1 with the anniversary sentence removed, weeks 2-5")
    wi = run(inject=True)
    for a, b in [("marisol", "kevin"), ("daniel", "kevin"), ("marisol", "daniel")]:
        mb = pooled_matrix(weeks, a, b, {2, 3, 4, 5}); mi = pooled_matrix(wi, a, b, {2, 3, 4, 5})
        kb, _ = pooled_kappa(weeks, a, b, {2, 3, 4, 5}); ki, _ = pooled_kappa(wi, a, b, {2, 3, 4, 5})
        print(f"  {a}-{b}: window x draft cell {cell(mb, 'decline_window', 'draft_deferral')} -> {cell(mi, 'decline_window', 'draft_deferral')}; kappa {kb:.3f} -> {ki:.3f}")
    fi = sum(wk["final"][t] == wk["required"][t] for wk in wi[1:] for t in wk["final"])
    fb = sum(wk["final"][t] == wk["required"][t] for wk in weeks[1:] for t in wk["final"])
    an_i = sum(1 for wk in wi[1:] for t in wk["anniv"] if t in wk["final"] and wk["final"][t] != wk["required"][t])
    an_n = sum(len(wk["anniv"]) for wk in wi[1:])
    print(f"  final labels right weeks 2-5: {fb} -> {fi} of {sum(len(wk['final']) for wk in wi[1:])}; anniversary finals wrong under injection {an_i}/{an_n}")
    import prelabel as P
    SEL = AB = AB2 = None
    if P.LOCAL:
        P.LB.banner("selection study and automation bias use local-model pre-labels")
    if not P.available():
        print("== Selection study and automation bias (REAL pre-labels)")
        P.LB.skip("this section", "out/prelabel.jsonl", "./run_all.sh run")
    else:
        print("== Selection study on 480 traces (REAL pre-labels; Compass failures from the fixture)")
        SEL, maj = selection()
        print("  ", json.dumps({k: v for k, v in SEL.items() if k != "prelabel"}, default=str))
        print("  pre-labeller:", json.dumps(SEL["prelabel"]))
        print("== Automation bias, SIMULATED readers with REAL pre-label suggestions (p_wrong 0.07, p_right 0.6)")
        AB = automation_bias(maj)
        for k, v in AB.items():
            print(f"  {k}: kappa {v['kappa']}, accuracy {v['acc']:.1%}, agreed but wrong {v['agreed_wrong']} of {v['n']}; Compass failures hidden by an agreed label {v['hidden_compass_failures']} of {v['compass_failures']}")
        AB2 = automation_bias(maj, p_wrong=0.2)
        print("  sensitivity p_wrong 0.2:", {k: (v["kappa"], v["agreed_wrong"], v["hidden_compass_failures"]) for k, v in AB2.items()})
    print("== Bootstrap 95% intervals, Marisol-Daniel kappa (2,000 resamples)")
    from truss.adjudication import bootstrap_kappa
    for wks in ({1}, {2}, {3}, {4}, {2, 3, 4}):
        la, lb = [], []
        for wk in weeks:
            if wk["week"] in wks:
                for k, v in wk["readings"].items():
                    if not k.startswith("a-") and "marisol" in v and "daniel" in v:
                        la.append(v["marisol"]); lb.append(v["daniel"])
        lo_, hi_ = bootstrap_kappa(la, lb)
        print(f"  weeks {sorted(wks)}: kappa {kappa(la, lb):.3f}, interval {lo_:.2f} to {hi_:.2f}, n {len(la)}")
    print("== Expert hours a week (Grace or Ben: rulings, audit, 30-minute session)")
    print("  ", [round(wk["adj_minutes"] / 60 + 0.5, 2) for wk in weeks])
    print("== Compass's hardship failure rate from the final labels (cannot_tell excluded)")
    allk = alln = 0
    for wk in weeks:
        f = [t for t in wk["final"] if wk["final"][t] != "cannot_tell"]
        k = sum(wk["compass"][t] != wk["final"][t] for t in f); tk = sum(wk["compass"][t] != wk["required"][t] for t in f)
        an = sum(1 for t in f if t in wk["anniv"] and wk["compass"][t] != wk["final"][t])
        lo_, hi_ = wilson(k, len(f)); allk += k; alln += len(f)
        print(f"  week {wk['week']}: {k}/{len(f)} ({k / len(f):.1%}, Wilson {lo_:.3f} to {hi_:.3f}); fixture truth {tk}; anniversary failures {an}")
    lo_, hi_ = wilson(allk, alln)
    print(f"  five weeks: {allk}/{alln} ({allk / alln:.1%}, Wilson {lo_:.3f} to {hi_:.3f})")
    wo = [(t, wk["final"][t]) for wk in weeks for t in wk["final"] if wk["final"][t] not in ("cannot_tell", "draft_deferral")
          and wk["compass"][t] == "draft_deferral"]
    print(f"  wrong offers (Compass drafted a deferral the final label does not allow): {len(wo)}/{alln} {wo}")
    true_wo = [t for t, _ in wo if any(wk["required"].get(t) not in (None, "draft_deferral") for wk in weeks)]
    from scipy.stats import beta
    for k in sorted({len(wo), len(true_wo)}):
        print(f"  one-sided 95% upper bound with {k} wrong offers in {alln}: {beta.ppf(0.95, k + 1, alln - k):.2%}")
    print(f"  of these, wrong offers under the fixture's truth: {true_wo}")
    print("== Final labels over five weeks")
    tot = sum(s["final_n"] for s in S); right = sum(s["final_right"] for s in S)
    lo, hi = wilson(right, tot)
    print(f"  {right}/{tot} final labels equal the policy's answer ({right / tot:.1%}; Wilson 95% {lo:.3f} to {hi:.3f}); pending {sum(s['pending'] for s in S)}")
    json.dump({"stats": S, "qual": q, "k_md": [k_md, n_md], "k1": [k1, n1], "costs": C, "designs": D, "debts": debts,
               "debt13": reg13, "selection": SEL, "ab": AB, "ab2": AB2,
               "inject": {f"{a}-{b}": [cell(pooled_matrix(weeks, a, b, {2, 3, 4, 5}), 'decline_window', 'draft_deferral'),
                                       cell(pooled_matrix(wi, a, b, {2, 3, 4, 5}), 'decline_window', 'draft_deferral'),
                                       pooled_kappa(weeks, a, b, {2, 3, 4, 5})[0], pooled_kappa(wi, a, b, {2, 3, 4, 5})[0]]
                          for a, b in [("marisol", "kevin"), ("daniel", "kevin"), ("marisol", "daniel")]},
               "inject_matrix_dk": pooled_matrix(wi, "daniel", "kevin", {2, 3, 4, 5}),
               "base_matrix_dk": pooled_matrix(weeks, "daniel", "kevin", {2, 3, 4, 5}),
               "w1_matrix_mk": pooled_matrix(weeks, "marisol", "kevin", {1}), "w1_matrix_md": m1o,
               "labels": L}, open(P.LB.pick(HERE, HERE / "out/lab.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
