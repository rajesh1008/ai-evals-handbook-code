"""Chapter 22 failure injection (REAL runs, cached): the 'reviewer-ready' prompt. Verdict on the first
line, then a four-heading explanation written for a compliance reviewer who will not open the trace.
The critiques read better; the verdicts get worse. Run: python3 inject.py"""
import json
from collections import Counter

import common as C

print("Failure injection: the reviewer-ready prompt against the shipped critique-first prompt (held-out 200)")
L = {}
for run in ("v2", "v3"):
    rs = [r for r in C.rows(run) if r["split"] == "test"]
    tb = C.table([r["truth"] for r in rs], [r["verdict"] for r in rs], [r["kind"] for r in rs])
    conv = [r["convincing"] for r in rs if r["convincing"]]
    dates = sum(len(C.RA.extract_dates(r["text"])) for r in rs) / len(rs)
    win = sum("window" in r["claims_wrong"] for r in rs)
    cons = Counter(r["consistency"] for r in rs)
    words = sum(r["words"] for r in rs) / len(rs)
    label = "critique first (shipped)" if run == "v2" else "reviewer-ready (verdict first)"
    print(f"  {label:32s} TPR {tb['tp']}/{tb['P']}  TNR {tb['tn']}/{tb['N']} ({C.ci(tb['tnr_ci'])})  kappa {tb['kappa']:.3f}  errors {sum(r['err'] for r in rs)}")
    print(f"  {'':32s} reader convincing mean {sum(conv) / len(conv):.3f}, rated 5: {sum(c == 5 for c in conv)}/{len(conv)}; "
          f"words {words:.0f}; dates quoted {dates:.2f} a critique; window claim wrong {win}; consistency {dict(cons)}")
    L[run] = {"tp": tb["tp"], "P": tb["P"], "tn": tb["tn"], "N": tb["N"], "tnr_ci": tb["tnr_ci"], "kappa": tb["kappa"],
              "errors": sum(r["err"] for r in rs), "convincing": sum(conv) / len(conv), "fives": sum(c == 5 for c in conv),
              "words": words, "dates": dates, "window_wrong": win, "consistency": dict(cons),
              "tokens_out": sum(r["tokens_out"] for r in rs) / len(rs)}
    if run == "v3":
        rs_all = C.add_flags(rs, 104.5)
        ev = C.RA.evaluate_flag(rs_all, ["f_window"], production=lambda r: r["stratum"] == "random")
        print(f"  {'':32s} window claim check on its critiques: catches {ev['caught']}/{ev['errors']} flagging {ev['flagged']}/{ev['n']}")
        L["v3_flag"] = ev
        e = Counter((r["kind"], r["edge"]) for r in rs if r["err"])
        print(f"  {'':32s} errors by kind: " + ", ".join(f"{k}{'*' if ed else ''} {n}" for (k, ed), n in e.most_common()))
        L["v3_err_kinds"] = {f"{k}{'*' if ed else ''}": n for (k, ed), n in e.items()}
d = C.RA.divergence({"convincing": L["v2"]["convincing"], "errors": L["v2"]["errors"], "n": 200},
                    {"convincing": L["v3"]["convincing"], "errors": L["v3"]["errors"], "n": 200})
print(f"  divergence check: admit {d['admit']}; reasons {d['reasons']}")
L["divergence"] = d
json.dump(L, open(C.F.__file__.replace("fixture.py", "out/inject.json"), "w"), indent=1, default=str)
