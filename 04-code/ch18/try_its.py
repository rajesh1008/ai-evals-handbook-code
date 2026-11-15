"""Three Try It Yourself variations on the Chapter 18 lab."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import build_production, draw_labeled, SEED
from truss.reportcard import (
    as_indicator, ppi_interval, human_only_interval, rogan_gladen,
    kappa_interval,
)
from truss.judge import confusion, rates
from truss.fields import wilson


def pct(x):
    return "nan" if x != x else f"{100 * x:.2f}%"


def main():
    traces = build_production()
    labeled, _ = draw_labeled(traces)
    out = {}

    print("=" * 100)
    print("TRY IT 1: Human-only interval as you grow the labelled set (50, 100, 200, 300)")
    print("=" * 100)
    y_all = as_indicator([t["gold"] for t in labeled])
    rows = []
    for n in (50, 100, 200, 300):
        y = y_all[:n]
        h = human_only_interval(y)
        w = wilson(int(round(h["p"] * n)), n)
        rec = {"n": n, "fails": int(round(h["p"] * n)), "p": h["p"],
               "wald_width": h["ci"][1] - h["ci"][0],
               "wilson": w, "wilson_width": w[1] - w[0]}
        rows.append(rec)
        print(f"  n={n:3d}  fails {rec['fails']}/{n} = {pct(h['p'])}  "
              f"Wilson {pct(w[0])} to {pct(w[1])}  width {w[1]-w[0]:.4f}")
    out["try1"] = rows

    print()
    print("=" * 100)
    print("TRY IT 2: PPI using only the first 200 labels, then all 300")
    print("=" * 100)
    f_n = as_indicator([t["judge"] for t in labeled])
    f_N = as_indicator([t["judge"] for t in traces])
    for n in (200, 300):
        pp = ppi_interval(y_all[:n], f_n[:n], f_N)
        print(f"  n={n}  PPI {pct(pp['p'])}  interval {pct(pp['ci'][0])} to {pct(pp['ci'][1])}  "
              f"width {pp['ci'][1]-pp['ci'][0]:.4f}  rectifier {pp['rectifier']:+.5f}")
        out[f"try2_n{n}"] = pp

    print()
    print("=" * 100)
    print("TRY IT 3: What if you published the raw judge rate as Compass's rate?")
    print("=" * 100)
    raw_k = sum(t["judge"] == "fail" for t in traces)
    raw_n = len(traces)
    raw = raw_k / raw_n
    true = sum(t["gold"] == "fail" for t in traces) / raw_n
    gold = [t["gold"] for t in labeled]
    judge = [t["judge"] for t in labeled]
    rt = rates(confusion(gold, judge))
    rg = rogan_gladen(raw, rt["tpr"], rt["tnr"])
    print(f"  raw judge {raw_k}/{raw_n} = {pct(raw)}")
    print(f"  planted truth {pct(true)}")
    print(f"  Rogan-Gladen {pct(rg['p'])}")
    print(f"  absolute error if you publish raw: {abs(raw - true):.5f} ({abs(raw-true)*100:.2f} points)")
    print(f"  absolute error if you publish RG:  {abs(rg['p'] - true):.5f} ({abs(rg['p']-true)*100:.2f} points)")
    out["try3"] = {"raw": raw, "true": true, "rg": rg["p"],
                   "err_raw": abs(raw - true), "err_rg": abs(rg["p"] - true)}

    (HERE / "out" / "try_its.json").write_text(json.dumps(out, indent=2, default=str))
    print("wrote", HERE / "out" / "try_its.json")


if __name__ == "__main__":
    main()
