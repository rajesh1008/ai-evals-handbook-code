"""Chapter 8 Try It Yourself, three variations.
1. Game the amended wrong-fee card: a release that defers every fee question.
2. Take polish and leniency out of the simulated 1-to-5 readers: does the scale study still favour binary?
3. Make the composite make-or-break: any gate metric that worsens sets the score to zero."""
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
from truss import metrics as M  # noqa: E402
from truss.taxonomy import kappa  # noqa: E402
import february as FEB  # noqa: E402
import march as MAR  # noqa: E402
import suite as SU  # noqa: E402
import compass_sim as C  # noqa: E402

mar = MAR.build()
fee = [r for r in mar if r["flow"] == "fee_explanation" and r["status"] != "abandoned"]
draw = sorted(random.Random(2026).sample(fee, 200), key=lambda r: r["trace_id"])
replay = MAR.pilot_fee_cases(SU.pilot_fee_ids()) + draw
card = SU.cards()[0][1]
card.amend("2027-03-19", "deferred counts as pass", deferred_as="pass")

print("== 1. A release that defers every fee question")
prod = [C.reply(r, "production")["outcome"] for r in replay]
lazy = ["deferred"] * len(replay)
for name, o in (("production", prod), ("defer-everything", lazy)):
    m = M.measure(card, o)
    print(f"  {name:<17} wrong {m['fail']}/{m['n']} ({m['rate']:.1%}); deferred {m['deferred']} ({m['deferred'] / len(o):.0%})")
print("  The card passes a release that answers nothing. Add a deferral alert (say 15%, owner the lead) and the")
print("  companion count catches it; under v1.0 (deferred as fail) the same release scores 100% wrong.")
card0 = SU.cards()[0][1]
print(f"  v1.0 on defer-everything: {M.measure(card0, lazy)['rate']:.0%} wrong")

print("\n== 2. 1-to-5 readers with no polish effect and no leniency")
prod_r = {r["trace_id"]: C.reply(r, "production") for r in draw}
ws = [x["words"] for x in prod_r.values()]
mw, sw = st.mean(ws), st.pstdev(ws)
for polish, len_b in ((C.POLISH, C.READERS["Ben"]["leniency"]), (0.0, 0.0)):
    C.POLISH, C.READERS["Ben"]["leniency"] = polish, len_b
    lA = [C.likert(r, "lead", prod_r[r["trace_id"]]["outcome"], prod_r[r["trace_id"]]["words"], mw, sw) for r in draw]
    lB = [C.likert(r, "Ben", prod_r[r["trace_id"]]["outcome"], prod_r[r["trace_id"]]["words"], mw, sw) for r in draw]
    bA = [x <= 2 for x in lA]; bB = [x <= 2 for x in lB]
    print(f"  polish {polish:.2f}, Ben's leniency {len_b:+.2f}: exact {sum(a == b for a, b in zip(lA, lB)) / 200:.0%}, "
          f"weighted kappa {M.weighted_kappa(lA, lB):.2f}; 'wrong' at <=2: lead {sum(bA)}, Ben {sum(bB)}; "
          f"kappa on that cut {kappa(bA, bB):.2f}")
print("  Weighted kappa falls without polish: part of the 1-to-5 agreement was both readers liking longer replies.")
print("  The cut-point kappa rises but stays under the binary question's, and the cut is still a choice nobody wrote down.")

print("\n== 3. Make-or-break composite")
rate = {}
nab = [r for r in mar if r["status"] != "abandoned"]
for f in FEB.SHARES:
    rs = [r for r in nab if r["flow"] == f]
    rate[f] = 1 - sum(1 for r in rs if r["cause"]) / len(rs)
hard = [r for r in nab if r["flow"] == "hardship"]
st_ = [r for r in nab if r["flow"] == "statement_request"]
ref = sum(1 for r in hard if r["cause"] == "H_refused") / len(hard)
ye = sum(1 for r in st_ if r["cause"] == "S_yearend") / len(st_)
trade = dict(rate); trade["statement_request"] += ye; trade["hardship"] -= ref
for name, r in (("March", rate), ("trade (FM-18 fixed, FM-20 doubled)", trade)):
    mean, _ = M.composite(r, FEB.SHARES)
    gate_ok = r["hardship"] >= rate["hardship"]
    print(f"  {name:<36} weighted mean {mean:.3f}; make-or-break {mean if gate_ok else 0.0:.3f}")
