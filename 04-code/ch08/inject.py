"""Chapter 8 failure injection: a generic metric that rewards verbosity.
The vendor dashboard's 'answer completeness' (share of eight fee-schedule terms a reply mentions)
is put beside MC-02 on the fee replay set. A length-stratified table exposes it."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
import json  # noqa: E402
import random  # noqa: E402
from truss import metrics as M  # noqa: E402
import march as MAR  # noqa: E402
import suite as SU  # noqa: E402
import compass_sim as C  # noqa: E402

mar = MAR.build()
fee = [r for r in mar if r["flow"] == "fee_explanation" and r["status"] != "abandoned"]
draw = sorted(random.Random(2026).sample(fee, 200), key=lambda r: r["trace_id"])
replay = MAR.pilot_fee_cases(SU.pilot_fee_ids()) + draw
BANDS = [("under 80", 0, 80), ("80 to 119", 80, 120), ("120 to 159", 120, 160), ("160 to 219", 160, 220), ("220 and over", 220, 10**6)]
R = {}
for rel in ("production", "rc-0322-1"):
    rows = []
    for r in replay:
        x = C.reply(r, rel)
        if x["outcome"] == "deferred":
            continue
        rows.append({"id": r["trace_id"], "words": x["words"], "complete": x["terms"] / 8, "wrong": x["outcome"] == "fail"})
    t = M.length_table(rows, "complete", "wrong", "words", BANDS)
    b = M.length_bias(rows, "complete", "wrong", "words")
    mean_c = sum(r["complete"] for r in rows) / len(rows)
    mean_c_wrong = sum(r["complete"] for r in rows if r["wrong"]) / max(1, sum(r["wrong"] for r in rows))
    print(f"\n{rel}: {len(rows)} replies that state a fee; mean completeness {mean_c:.2f}; "
          f"mean completeness of the wrong ones {mean_c_wrong:.2f}")
    print(f"  {'words':<14}{'n':>5}{'completeness':>14}{'wrong fee':>12}")
    for x in t:
        lo, hi = x["wilson"]
        print(f"  {x['band']:<14}{x['n']:>5}{x['mean_score']:>14.2f}{x['fail']:>6} ({x['fail_rate']:.1%})" if x["n"] else f"  {x['band']:<14}{0:>5}")
    print(f"  Spearman with length {b['rho_length']:.2f}; with being right {b['rho_correct']:.2f}; "
          f"length_bias flag: {b['flag']}")
    R[rel] = {"table": t, "bias": b, "mean": mean_c, "mean_wrong": mean_c_wrong, "n": len(rows)}
json.dump(R, open(HERE / "out" / "inject.json", "w"), indent=1, default=str)
