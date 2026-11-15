"""Chapter 7 lab: draw February's fifty, join the notebook, measure agreement, adjudicate,
release taxonomy v0.3, run the FM-22 census, restate the weekly draws, and cost the notebook.
Run: python3 lab.py   (writes out/lab.json, out/notebook-feb.csv/.md, out/taxonomy-v0.3.json/.md)"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
import truss
from truss import notebook as NBK
from truss import sampling as S
from truss import taxonomy as T
from truss.taxonomy import Mode, Taxonomy
import february as FEB
import notebook_data as D

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
R = {}
CODE = {"F_waive": "FM-06", "X_wrongloan": "FM-22", "P_perdiem": "FM-19", "P_goodthru": "FM-19",
        "X_invent": "FM-24", "L_early": "FM-11", "L_state": "FM-12", "L_address": "FM-23",
        "H_income": "FM-01", "H_refused": "FM-20", "H_ignored": "FM-14", "H_approval": "FM-03",
        "A_date": "FM-07", "A_second": "FM-08", "S_month": "FM-17", "S_yearend": "FM-18"}
FRAME_SQL = ("SELECT trace_id FROM traces WHERE started_at >= '2027-02-01' AND started_at < '2027-02-15' "
             "AND status != 'abandoned'")


def head(s):
    print(f"\n== {s}")


# ---- 1. frame and draw
frame = FEB.build()
risk = FEB.risk_fn(frame)
fr = [r for r in frame if r["status"] != "abandoned"]
draw = NBK.pps_quota(fr, "flow", FEB.QUOTAS, risk, seed=2026)
ids = [t for t, _, _ in draw]
FEB.apply_facts(frame, ids)
by = {r["trace_id"]: r for r in frame}
fr = [r for r in frame if r["status"] != "abandoned"]
assert all(t in {r["trace_id"] for r in fr} for t in ids)
man = S.manifest("ea-2027-02", "risk-weighted within quotas", {"quotas": FEB.QUOTAS, "risk": "Chapter 3 score"},
                 FRAME_SQL, [r["trace_id"] for r in fr], [(t, w) for t, _, w in draw], 2026, truss.__version__)
(OUT / "manifest-ea-2027-02.json").write_text(S.dumps(man))
head("1. the frame and the draw")
print(f"window Mon 1 - Sun 14 Feb 2027: {len(frame)} conversations, {frame[0]['trace_id']} to {frame[-1]['trace_id']}")
print(f"frame (abandoned excluded, declared): {len(fr)}; frame hash {man['frame_sha256']}; truss {truss.__version__}")
groups = ["fee", "payoff and lien", "hardship", "account and statement"]
fshare = {g: sum(r["group"] == g for r in fr) / len(fr) for g in groups}
sshare = {g: sum(by[t]["group"] == g for t in ids) / 50 for g in groups}
for g in groups:
    print(f"  {g:<22} frame {fshare[g]:5.1%}  sample {sshare[g]:5.1%}  ({round(sshare[g] * 50)} traces)")
te_f = sum(r["tool_error"] for r in fr) / len(fr)
te_s = sum(by[t]["tool_error"] for t in ids)
print(f"tool-error conversations: frame {te_f:.1%} ({sum(r['tool_error'] for r in fr)}), sample {te_s} of 50 ({te_s / 50:.0%})")
print(f"first trace {ids[0]}, last {ids[-1]}; hardship weight range "
      f"{min(w for _, s, w in draw if s == 'hardship'):.1f}-{max(w for _, s, w in draw if s == 'hardship'):.1f}")
R["frame"] = {"window": len(frame), "frame": len(fr), "first": frame[0]["trace_id"], "last": frame[-1]["trace_id"],
              "fshare": fshare, "sshare": sshare, "tool_error_frame": te_f, "tool_error_sample": te_s,
              "hash": man["frame_sha256"], "ids": ids}

# ---- 2. the notebook, checked against the traces
entries = []
for n, t in enumerate(ids, 1):
    v, fp, oc, cl, dec, code, sec = D.NB[n]
    r = by[t]
    planted = CODE.get(r["cause"])
    final_fail = dec in ("existing mode", "new mode", "open code")
    assert final_fail == bool(planted), (n, t, dec, r["cause"])
    assert not planted or planted == code, (n, planted, code)
    entries.append(NBK.Entry(n, t, r["flow"], "fail" if final_fail or v == "fail" else "pass", fp, oc, cl, dec, code, sec,
                             "evaluation lead"))
NBK.write(entries, OUT / "notebook-feb.csv")
(OUT / "notebook-feb.md").write_text(NBK.to_markdown(entries) + "\n")
fails = [e for e in entries if e.decision in ("existing mode", "new mode", "open code")]
flagged = [e for e in entries if e.verdict == "fail"]
head("2. the notebook")
print(f"flagged at first pass or after: {len(flagged)}; failures after decisions: {len(fails)}")
for sec, lo, hi in (("fee 1-10", 1, 10), ("payoff and lien 11-25", 11, 25), ("hardship 26-40", 26, 40), ("account and statement 41-50", 41, 50)):
    f = [e for e in fails if lo <= e.n <= hi]
    print(f"  {sec:<28} failures {len(f):>2}: {', '.join(f'{e.n} {e.code}' for e in f)}")
print("decisions:", dict(Counter(e.decision for e in entries)))
for e in entries:
    if e.n in D.EXCERPTS:
        print(f"  excerpt {e.n} {e.trace_id} {e.flow} {by[e.trace_id]['started_at']}")
R["notebook"] = [e.__dict__ | {"started_at": by[e.trace_id]["started_at"]} for e in entries]

# ---- 3. saturation
sat = NBK.saturation(entries)
head("3. saturation (clusters among flagged traces, in reading order)")
print(" ".join(f"{n}:{c}" for n, _, c in sat if n % 5 == 0))
first_seen = {}
for e in sorted(flagged, key=lambda e: e.n):
    first_seen.setdefault(e.cluster, e.n)
print("cluster first seen at:", first_seen)
last_new = max(first_seen.values())
print(f"last new cluster at trace {last_new}; clusters {len(first_seen)}; new in last ten {sum(v > 40 for v in first_seen.values())}")
R["saturation"] = sat
R["first_seen"] = first_seen

# ---- 4. agreement and adjudication
def pre_label(e):
    if e.n in D.FIRST_PRE:
        return D.FIRST_PRE[e.n]
    return e.code if e.decision == "existing mode" else "pass"

first = [NBK.Entry(e.n, e.trace_id, e.flow, "pass" if pre_label(e) == "pass" else "fail",
                   code="" if pre_label(e).startswith("open:") else pre_label(e).replace("pass", ""),
                   cluster=pre_label(e)[5:] if pre_label(e).startswith("open:") else "") for e in entries]
second = []
for e, x in zip(entries, first):
    lab = D.SECOND_DIFF.get(e.n, x.label())
    second.append(NBK.Entry(e.n, e.trace_id, e.flow, "pass" if lab == "pass" else "fail",
                            code="" if lab.startswith("open:") or lab == "pass" else lab,
                            cluster=lab[5:] if lab.startswith("open:") else "", annotator=D.SECOND_WHO(e.n)))
ag = NBK.agreement(first, second)
head("4. agreement before adjudication (first reader vs Grace on 26-40, Ryan on the rest)")
print(f"traces {ag['n']}; verdict agree {ag['verdict_agree']} (kappa {ag['verdict_kappa']:.2f}); "
      f"label agree {ag['label_agree']} (kappa {ag['label_kappa']:.2f})")
for part, lo, hi in (("Grace, hardship", 26, 40), ("Ryan, other flows", 1, 50)):
    sel = [i for i, e in enumerate(first) if (lo <= e.n <= hi) and (part.startswith("Grace") or not 26 <= e.n <= 40)]
    k = T.kappa([first[i].label() for i in sel], [second[i].label() for i in sel])
    agree = sum(first[i].label() == second[i].label() for i in sel)
    print(f"  {part}: {agree}/{len(sel)} labels agree, kappa {k:.2f}")
adj = NBK.adjudicate(ag["disagreements"], D.RULINGS)
for a in adj:
    print(f"  {a['n']:>2} {a['trace_id']} {a['kind']:<7} first {a['first']:<28} second {a['second']:<26} -> {a['final']:<6} [{a['kind_of_question']}; {a['decider']}]")
print("settled by:", dict(Counter(a["kind_of_question"] for a in adj)))
R["agreement"] = {k: ag[k] for k in ("n", "verdict_agree", "label_agree", "verdict_kappa", "label_kappa")}
R["adjudication"] = adj
R["pairs"] = [(x.label(), y.label()) for x, y in zip(first, second)]

# ---- 5. coverage under v0.2, cluster decisions
t02 = Taxonomy.from_json((HERE.parents[0] / "ch06/out/taxonomy-v0.2.json").read_text())
assert t02.digest() == "41041db69244"
fit02 = [e for e in fails if e.code in t02.modes and t02.modes[e.code].status == "active"]
cov = T.coverage([{"code": e.code if e in fit02 else None, "fit": e in fit02} for e in fails])
nm, nm_ci = T.new_mode_rate([{"code": e.code if e in fit02 else None, "fit": e in fit02} for e in fails], 50)
head("5. v0.2 against February's fifty")
print(f"failures {len(fails)}; fitted by a v0.2 mode {len(fit02)} ({cov['fitted_share']:.0%}, Wilson "
      f"{cov['fitted_ci'][0]:.0%}-{cov['fitted_ci'][1]:.0%}); new-mode rate {nm * 100:.0f} per 100 read "
      f"(Wilson {nm_ci[0] * 100:.1f}-{nm_ci[1] * 100:.1f}); v0.2 holdout bound was 1.8 per 100")
CL = {  # cluster: harms, fits_existing, one_fix_owner, traces, critical, confirmed elsewhere
    "wrong loan used": (True, False, True, 3, True, 0),
    "answer after tool error": (True, False, True, 2, False, 0),
    "letter to old address": (True, False, True, 1, False, 1),     # t-071074, January's open code
    "courtesy waiver": (False, False, True, 1, False, 0),
    "verbose or repeated": (False, False, False, 3, False, 0),
    "borrower left": (False, False, False, 1, False, 0),
}
dec = {c: NBK.cluster_decision(*v[:4], critical=v[4], confirmed_elsewhere=v[5]) for c, v in CL.items()}
for c, d in dec.items():
    print(f"  {c:<26} -> {d}")
assert dec["courtesy waiver"] == "noise"  # the rule says noise; the notebook records it as a policy question
R["coverage_v02"] = {"failures": len(fails), "fitted": len(fit02), "share": cov["fitted_share"],
                     "ci": cov["fitted_ci"], "new_mode_per100": nm * 100, "new_mode_ci": [x * 100 for x in nm_ci]}
R["cluster_decisions"] = dec

# ---- 6. taxonomy v0.3
LEAD, RYAN, GRACE = "evaluation lead", "Ryan Mitchell (engineering)", "Grace Holloway (loan officers)"
t03 = Taxonomy.from_json((HERE.parents[0] / "ch06/out/taxonomy-v0.2.json").read_text())
t03.add(Mode("FM-22", "tool called on a loan other than the one the borrower named",
             ("fee_explanation", "payoff_letter", "hardship", "account_question"),
             "The borrower named a loan and Compass called a tool on a different loan on the account.",
             test="Did the borrower name a loan, and does any tool call in the conversation carry a different loan ID?",
             excludes="The borrower named no loan and Compass answered about one of two: FM-08.",
             layer=1, owner=RYAN, severity="critical", added_in="0.3", source="error analysis Feb 2027"),
        "three traces in three flows (6, 13, 33), one a wrong hardship offer; one cause in the tool-call wrapper")
t03.add(Mode("FM-23", "lien release letter mailed to an address the borrower said had changed", ("lien_release",),
             "The borrower said their address had changed and the release letter went to the address on file.",
             test="Did the borrower state a new address, and was the lien letter requested to a different one?",
             excludes="A release naming the wrong title state is FM-12.",
             layer=2, owner=RYAN, severity="high", added_in="0.3", source="error analysis Jan and Feb 2027"),
        "January open code t-071074 and February trace 21; one fix (apply the address before mailing)")
t03.add(Mode("FM-24", "answer given as if a failed tool call had returned", ("fee_explanation", "payoff_letter",
             "account_question", "lien_release", "hardship", "statement_request"),
             "A tool span ended in error and the reply states a figure or a done action that call should have supplied.",
             test="Did a tool span end in error, with a reply that states a figure or action that tool was called for?",
             excludes="A reply that says the tool failed and offers another route is a pass.",
             layer=1, owner=RYAN, severity="high", added_in="0.3", source="error analysis Feb 2027"),
        "two traces in two flows (15, 43); the February wrapper returns an empty result on error")
t03.reword("FM-04", "test read the eligibility tool, which can be called on the wrong loan (trace 33)",
           test="Did Compass offer a deferral on a loan whose account history shows a deferral in the previous twelve months?")
t03.reword("FM-08", "exclusion line against FM-22",
           test="Did the loan tool return two or more loans, the borrower name none, and the reply address one without saying so?",
           excludes="The borrower named a loan and a tool was called on another: FM-22.")
t03.reword("FM-14", "Grace's ruling on trace 32",
           test="Did the borrower ask to speak to, or be called by, a person while the hand-off queue was open, with no hand-off attempted?")
rel = t03.release("minor")
probs = t03.validate()
assert not probs, probs
(OUT / "taxonomy-v0.3.json").write_text(t03.to_json())
md = [f"# Compass failure taxonomy v{t03.version} (digest {rel['digest']}), released Mon 22 Feb 2027", "",
      "| Code | Name | Layer | Owner | Severity | Status | Inclusion test |", "|---|---|---|---|---|---|---|"]
for m in sorted(t03.modes.values(), key=lambda m: m.code):
    md.append(f"| {m.code} | {m.name} | {m.layer} | {m.owner} | {m.severity} | {m.status} | {m.test} |")
md += ["", "Changes:"] + [f"- {c['op']} {', '.join(c['codes'])}: {c['reason']}" for c in rel["changes"]]
(OUT / "taxonomy-v0.3.md").write_text("\n".join(md) + "\n")
head("6. taxonomy v0.3")
st = Counter(m.status for m in t03.modes.values())
print(f"{rel['from']} -> {rel['to']}, digest {rel['digest']}; {st['active']} active, {st['closed']} closed, {st['retired']} retired")
for c in rel["changes"]:
    print(f"  {c['op']:<7} {', '.join(c['codes']):<8} {c['reason']}")
fit03 = [e for e in fails if e.code in t03.modes]
print(f"in-sample fitted coverage under v0.3: {len(fit03)}/{len(fails)} (circular: the modes were written from these traces)")
R["v03"] = {"digest": rel["digest"], "active": st["active"], "closed": st["closed"], "retired": st["retired"],
            "changes": rel["changes"]}

# ---- 7. checks: coverage before and after
CHECKS = {"FM-01": [3], "FM-03": [3], "FM-04": [1, 3], "FM-06": [1, 3], "FM-07": [3], "FM-08": [3],
          "FM-11": [3], "FM-12": [3], "FM-14": [3], "FM-15": [3], "FM-16": [3], "FM-17": [3], "FM-18": [3],
          "FM-19": [3], "FM-20": [3], "FM-21": [3]}
cc02 = T.check_coverage(t02, CHECKS)
CHECKS3 = dict(CHECKS, **{"FM-22": [1], "FM-24": [1]})
cc03 = T.check_coverage(t03, CHECKS3)
head("7. check coverage (a check at or below the mode's lowest layer)")
print(f"v0.2: {cc02['with_check']}/{cc02['modes']} = {cc02['share']:.0%}; missing {cc02['missing']}")
print(f"v0.3: {cc03['with_check']}/{cc03['modes']} = {cc03['share']:.0%}; missing {cc03['missing']}")
R["check_cov"] = {"v02": [cc02["with_check"], cc02["modes"]], "v03": [cc03["with_check"], cc03["modes"]],
                  "missing03": cc03["missing"]}

# ---- 8. census: the FM-22 and FM-24 checks over the whole window
head("8. census over all conversations 1-14 Feb (layer-one checks, every trace)")
loan_flows = [r for r in frame if r["flow"] in FEB.LOAN_FLOWS]
f22 = [r for r in frame if r["cause"] == "X_wrongloan"]
named = [r for r in loan_flows if r["named_by_digits"]]
print(f"loan-flow conversations {len(loan_flows)}; borrower named a loan by its last four digits {len(named)}; "
      f"FM-22 flagged {len(f22)} ({len(f22) / len(loan_flows):.1%} of loan-flow, {len(f22) / len(named):.0%} of named-by-digits)")
print("  by flow:", dict(Counter(r["flow"] for r in f22)))
off = [r for r in f22 if r["flow"] == "hardship" and r["offer_drafted"]]
wrong = [r for r in off if r["offered_loan_recent_deferral"]]
hs_off = [r for r in frame if r["flow"] == "hardship" and r["offer_drafted"]]
print(f"  hardship offers drafted in window {len(hs_off)}; on the wrong loan {len(off)}; of those, offered loan had a "
      f"deferral in the last 12 months (wrong offers) {len(wrong)}: {[r['trace_id'] + ' ' + r['day'] for r in wrong]}")
in_sample = [r["trace_id"] for r in wrong if r["trace_id"] in ids]
print(f"  wrong offers in the fifty: {in_sample}")
f24 = [r for r in frame if r["cause"] == "X_invent"]
terr = [r for r in frame if r["tool_error"]]
print(f"FM-24 flagged {len(f24)} of {len(terr)} tool-error conversations ({len(f24) / len(terr):.0%}); by flow {dict(Counter(r['flow'] for r in f24))}")
lien_addr = sum(1 for r in frame if r["cause"] == "L_address")
print(f"FM-23 has no layer-one check; its layer-two detector is not built (planted in fixture: {lien_addr}, not reported)")
R["census"] = {"loan_flow": len(loan_flows), "named": len(named), "f22": len(f22), "f22_by_flow": dict(Counter(r["flow"] for r in f22)),
               "hs_offers": len(hs_off), "offers_wrong_loan": len(off), "wrong_offers": [(r["trace_id"], r["day"]) for r in wrong],
               "f24": len(f24), "tool_errors": len(terr)}

# ---- 9. restatement of the weekly draws, 14 Dec - 24 Jan
head("9. restatement under v0.2 (owed from Chapter 6)")
tot = sum(c for v in D.RESTATE.values() for *_, c in v)
changed = sum(c for v in D.RESTATE.values() for a, b, c in v if a != b)
flipped = sum(c for v in D.RESTATE.values() for a, b, c in v if a == "pass" and b != "pass")
print(f"conversations re-read {tot}; labels changed {changed}; passes that became failures {flipped}")
for flow, rows in D.RESTATE.items():
    for a, b, c in rows:
        print(f"  {flow:<18} {a:<6} -> {b:<6} {c}")
k20 = sum(c for a, b, c in D.RESTATE["hardship"] if b == "FM-20")
lo, hi = T.wilson(k20, D.WEEKLY_HARDSHIP_READ)
print(f"FM-20 in the weekly hardship draws: {k20} in {D.WEEKLY_HARDSHIP_READ} = {k20 / D.WEEKLY_HARDSHIP_READ:.1%} (Wilson {lo:.1%}-{hi:.1%})")
R["restate"] = {"read": tot, "changed": changed, "flipped": flipped, "fm20": [k20, D.WEEKLY_HARDSHIP_READ, lo, hi]}

# ---- 10. hours
head("10. what the notebook cost")
MIN = {"fee_explanation": 6, "payoff_letter": 7, "lien_release": 8, "hardship": 12, "account_question": 4, "statement_request": 4}
read_min = Counter()
for t in ids:
    read_min[by[t]["flow"]] += MIN[by[t]["flow"]]
plan = [("draw, manifest, frame audit", "lead", 1, 30)]
plan += [(f"first reading: {f.replace('_', ' ')}", "lead", FEB.QUOTAS[f], MIN[f]) for f in FEB.QUOTAS]
plan += [("axial session", "lead", 1, 120),
         ("second reading: hardship", "Grace", 15, 10), ("second reading: other flows", "Ryan", 35, 3),
         ("adjudication (first reader)", "lead", 6, 15), ("adjudication: hardship", "Grace", 2, 15),
         ("adjudication: other flows", "Ryan", 4, 15),
         ("v0.3 release: tests, exclusions, crosswalk", "lead", 1, 120),
         ("FM-22 census check", "Ryan", 1, 90),
         ("restatement: statements", "lead", 30, 3), ("restatement: hardship", "Grace", 11, 10)]
H = NBK.hours(plan, {"lead": 85, "Ryan": 85, "Grace": 60})
by_person = Counter(); by_act = Counter()
for r in H["rows"]:
    by_person[r["person"]] += r["hours"]
    k = r["activity"].split(":")[0]
    by_act[k] += r["hours"]
for r in H["rows"]:
    print(f"  {r['activity']:<44} {r['person']:<6} {r['count']:>3} x {r['minutes']:>3} min = {r['hours']:5.2f} h  ${r['dollars']:7.2f}")
print(f"total {H['hours']:.1f} hours, ${H['dollars']:,.0f}; by person { {k: round(v, 1) for k, v in by_person.items()} }")
print(f"by activity { {k: round(v, 1) for k, v in by_act.items()} }")
reading = sum(r["hours"] for r in H["rows"] if r["activity"].startswith("first reading"))
print(f"first reading alone {reading:.1f} h ({reading / H['hours']:.0%}); per trace read {reading * 60 / 50:.1f} min")
R["hours"] = {"total": H["hours"], "dollars": H["dollars"], "by_person": dict(by_person), "by_activity": dict(by_act),
              "rows": H["rows"], "reading": reading}

json.dump(R, open(OUT / "lab.json", "w"), indent=1, default=str)
