"""Chapter 22 Try It Yourself (REAL runs, cached).
1. Verdict only: drop the critique and score the same 300 traces.
2. Evidence first: fill the record fields, then the verdict (held-out 200).
3. Flag by disagreement between two draws of the same prompt (100 held-out traces) against the claim check.
Run: python3 try_its.py"""
import json

import common as C

L = {}
print("Try It 1: verdict only, same rules, no critique")
for run in ("v2", "vonly"):
    for part in ("dev", "test"):
        rs = [r for r in C.rows(run) if r["split"] == part]
        tb = C.table([r["truth"] for r in rs], [r["verdict"] for r in rs], [r["kind"] for r in rs])
        print(f"  {run:6s} {part:4s} TPR {tb['tp']}/{tb['P']}  TNR {tb['tn']}/{tb['N']} ({C.ci(tb['tnr_ci'])})  kappa {tb['kappa']:.3f}  errors {sum(r['err'] for r in rs)}")
        L[f"{run}_{part}"] = {"tp": tb["tp"], "P": tb["P"], "tn": tb["tn"], "N": tb["N"], "kappa": tb["kappa"], "errors": sum(r["err"] for r in rs)}

print("Try It 2: evidence first (fields, then verdict), held-out 200")
R = C.J.load("proof")
ids = sorted(R)
tb = C.table([C.BY_ID[i]["truth"] for i in ids], [C.J.verdict(R[i]["text"]) for i in ids], [C.BY_ID[i]["kind"] for i in ids])
miss = [i for i in ids if C.BY_ID[i]["truth"] == "fail" and C.J.verdict(R[i]["text"]) != "fail"]
from collections import Counter
print(f"  TPR {tb['tp']}/{tb['P']} ({C.ci(tb['tpr_ci'])})  TNR {tb['tn']}/{tb['N']} ({C.ci(tb['tnr_ci'])})  kappa {tb['kappa']:.3f}  "
      f"errors {sum(C.J.verdict(R[i]['text']) != C.BY_ID[i]['truth'] for i in ids)}; misses by kind {dict(Counter(C.BY_ID[i]['kind'] for i in miss))}")
u = C.llm.usage(R.values())
print(f"  output tokens a call {u['out'] / len(ids):.0f}; cost a call ${u['cost'] / len(ids):.5f}")
L["proof"] = {"tp": tb["tp"], "P": tb["P"], "tn": tb["tn"], "N": tb["N"], "kappa": tb["kappa"],
              "errors": sum(C.J.verdict(R[i]["text"]) != C.BY_ID[i]["truth"] for i in ids), "miss_kinds": dict(Counter(C.BY_ID[i]["kind"] for i in miss))}

print("Try It 3: flag when two draws disagree (100 held-out traces) vs the window claim check")
V2, B = C.J.load("v2"), C.J.load("cue_base")
ids = sorted(B)
rows = {r["id"]: r for r in C.add_flags(C.rows("v2"), 104.5)}
err = {i: rows[i]["err"] for i in ids}
dis = {i: C.J.verdict(V2[i]["text"]) != C.J.verdict(B[i]["text"]) for i in ids}
win = {i: rows[i]["f_window"] for i in ids}
E = sum(err.values())
for name, fl in (("two draws disagree", dis), ("window claim wrong", win), ("either", {i: dis[i] or win[i] for i in ids})):
    print(f"  {name:20s} catches {sum(err[i] for i in ids if fl[i])}/{E} flagging {sum(fl.values())}/100")
    L[f"t3_{name}"] = {"caught": sum(err[i] for i in ids if fl[i]), "errors": E, "flagged": sum(fl.values())}
json.dump(L, open(C.F.__file__.replace("fixture.py", "out/try_its.json"), "w"), indent=1, default=str)
