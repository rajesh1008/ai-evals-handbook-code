"""Failure injection for Chapter 9: the payoff check (C-07) with the wrong day-count convention.
Three versions of the same check run over the 801 April payoff conversations:
  as shipped   - the convention read from each loan record (actual/365 consumer, actual/360 small business)
  30/360       - hard-coded, as in the mortgage library the first draft was copied from
  actual/365   - hard-coded, the convention that is right for 94% of the book
Second setting: Saguaro Coffee Roasters LLC, a small-business borrower who asked for a payoff three times.
Run: python3 inject.py"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
sys.path.insert(0, str(HERE.parents[0] / "ch08"))
from truss import checks as K  # noqa: E402
import april as A  # noqa: E402
import compass_checks as CC  # noqa: E402

rows = A.build()
pay_rows = [r for r in rows if r["flow"] == "payoff_letter"]
sag = sorted(random.Random(2026).sample([r["trace_id"] for r in pay_rows if not r["tool_error"]], 3))
A.SAGUARO.update(sag)
pay = [A.render(r) for r in pay_rows]


def product(t):
    q = CC.spans(t, "get_payoff_quote")
    lid = q[0]["args"]["loan_id"] if q else t["account"]["loans"][0]["loan_id"]
    return CC.loan_rec(t, lid)["product"]


prod = Counter(product(t) for t in pay)
print(f"April payoff conversations {len(pay)}; products {dict(prod)}; Saguaro Coffee Roasters LLC conversations {sag}")
out = {}
truth = {t["trace_id"] for t in pay if set(t["truth"]) & {"FM-19", "tool:sunday"}}
for name, conv in (("as shipped (loan record)", None), ("30/360 hard-coded", "30/360"), ("actual/365 hard-coded", "actual/365")):
    S = CC.suite(payoff_convention=conv)
    res, _ = S.run_all(pay)
    fl = {t["trace_id"] for t in pay if res[t["trace_id"]]["C-07"].outcome == K.FAIL}
    false = fl - truth
    byp = Counter(product(t) for t in pay if t["trace_id"] in false)
    missed = truth - fl
    print(f"\n{name}: C-07 fails {len(fl)} ({len(fl) / len(pay):.1%}); true {len(fl & truth)}; false {len(false)} by product "
          f"{dict(byp)}; real failures missed {len(missed)}")
    for t in sag:
        r = res[t]["C-07"]
        print(f"   Saguaro {t}: {r.outcome:<12} {r.evidence}")
    pd = [res[t["trace_id"]]["C-07"].data.get("per_diem_diff", 0) for t in pay if t["trace_id"] in false]
    if pd:
        print(f"   false flags: per diem gap mean ${sum(pd) / len(pd):+.2f}, all one sign: {all(x > 0 for x in pd) or all(x < 0 for x in pd)}")
    out[name] = {"fails": len(fl), "true": len(fl & truth), "false": len(false), "by_product": dict(byp),
                 "missed": len(missed), "saguaro": {t: [res[t]["C-07"].outcome, res[t]["C-07"].evidence] for t in sag}}
# what the defect would have done to the census and to the borrower
sb = [t for t in pay if product(t) == "small_business"]
print(f"\nsmall-business payoff conversations {len(sb)} of {len(pay)} ({len(sb) / len(pay):.1%})")
S0 = CC.suite()
r0, _ = S0.run_all(sb)
print("as shipped, their C-07 outcomes:", dict(Counter(r0[t["trace_id"]]["C-07"].outcome for t in sb)))
print("the gate rule 'every check flag is a real failure' is broken by the hard-coded convention; the census rate for "
      "MC-16 reads", f"{out['actual/365 hard-coded']['fails'] / len(pay):.1%} against {out['as shipped (loan record)']['fails'] / len(pay):.1%}")
(HERE / "out").mkdir(exist_ok=True)
(HERE / "out" / "inject.json").write_text(json.dumps({"saguaro": sag, "n": len(pay), "products": dict(prod),
                                                       "small_business": len(sb), "runs": out}, indent=1))
