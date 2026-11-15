"""Three Try-its — offline deterministic."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "truss"))
from truss.toolscape import run_all_platforms, wilson_upper, hardship_gate  # noqa: E402
from fixture import build_cases, N  # noqa: E402

def main():
    cases = build_cases()
    hi0 = wilson_upper(0, N)
    t1 = {"name": "wilson_upper_0_of_n", "n": N, "hi": hi0, "ok": hi0 < 0.005}
    rec = run_all_platforms(cases, "harbor-hardship-judge@2026-11-01")
    t2 = {"name": "six_platform_agree_admit", "admits": {k: v.admit for k,v in rec.items()}, "ok": all(v.admit for v in rec.values())}
    g = hardship_gate(platform="promptfoo", n=N, wrong_offers=2, judge_version="x")
    t3 = {"name": "two_wrong_offers_opens_gate", "admit": g.admit, "wilson_upper": g.wilson_upper, "ok": (not g.admit) and g.wilson_upper >= 0.005}
    out = {"try_its": [t1, t2, t3], "all_ok": all(t["ok"] for t in [t1,t2,t3])}
    Path(__file__).resolve().parent.joinpath("out/try_its.json").write_text(json.dumps(out, indent=2))
    print(out)
    return out

if __name__ == "__main__":
    main()
