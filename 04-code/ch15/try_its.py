"""Chapter 15 Try It Yourself variations.
1  move the composition audit's two thresholds and watch which segments fail
2  gate the REAL probe on one direction at a time, on accuracy, and on both
3  how long Victor waits for a bound under 0.5%, by true rate and by source of readings
Run: python3 try_its.py"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
import fixture as FX  # noqa: E402
import probe as PR  # noqa: E402
from truss import flowsuite as FS  # noqa: E402

G, F = FX.gold(), FX.frame()
R = {}
print(f"== 1. Composition audit thresholds on the {len(G)} gold labels")
R["t1"] = {}
for min_n, ratio in ((10, 0.5), (20, 0.5), (30, 0.5), (20, 0.8), (40, 0.8)):
    a = FS.composition_audit(G, F, FX.flags, min_n=min_n, min_ratio=ratio)
    R["t1"][f"{min_n}|{ratio}"] = a["failing"]
    print(f"  minimum {min_n:2d}, share at least {ratio:.0%} of traffic: {a['verdict']:6s} failing {a['failing']}")

print("\n== 2. One direction, accuracy, or both (REAL probe, two runs per prompt)")
if PR.LOCAL:
    PR.LB.banner("Try it 2 uses local-model probe replies")
if not PR.complete():
    PR.LB.skip("Try it 2", "out/probe.jsonl", "./run_all.sh run")
else:
    C = PR.cached()
    cs = {c["id"]: c for c in PR.cases()}
    req = {i: c["required"] for i, c in cs.items()}
    runs = {pv: [{i: PR.action(C[(i, pv, rep)]["raw"]) for i in cs} for rep in (1, 2)] for pv in PR.PROMPTS}
    R["t2"] = {}
    for pv in ("rc-0913-1", "rc-0915-2", "rc-0917-3"):
        g = FS.two_way_gate(req, runs["hardship-prompt-p7"], runs[pv])
        v = {"MC-01 only": "hold" if g["offer"]["new"] else "ship",
             "MC-17 only": "hold" if g["refusal"]["new"] else "ship",
             "accuracy only": "ship" if sum(g["accuracy"]["cand"]) > sum(g["accuracy"]["base"]) else "hold",
             "both": g["verdict"]}
        R["t2"][pv] = v
        print(f"  {pv}: " + "; ".join(f"{k} {x.upper()}" for k, x in v.items()))

print("\n== 3. Weeks until MC-01's bound is under 0.5%, if a fix brings the true rate to ...")
L = json.loads(PR.LB.pick(HERE, HERE / "out" / "lab.json").read_text())["F"]
have, g_wk, c_wk = L["drafted"], L["gold_wk"], L["census_wk"]
print(f"  replaying the fix on the gold gives {have} offers at once; 60 gold labels a week add {g_wk:.1f}, "
      f"120 add {2 * g_wk:.1f}; live traffic drafts {c_wk:.1f} a week")
R["t3"] = {}
for true in (0.0005, 0.001, 0.002, 0.003):
    n = FS.refine(true, 0.005)
    row = {"n": n, "gold_60": FS.weeks_to(n, have, g_wk), "gold_120": FS.weeks_to(n, have, 2 * g_wk),
           "census": FS.weeks_to(n, 0, c_wk)}
    R["t3"][str(true)] = row
    print(f"  {true:.2%}: {n} offers; gold {row['gold_60']:.1f} weeks at 60 labels, {row['gold_120']:.1f} at 120; "
          f"census {row['census']:.1f} weeks, if its checks catch every kind of wrong offer")
PR.LB.pick(HERE, HERE / "out" / "try_its.json").write_text(json.dumps(R, indent=1))
