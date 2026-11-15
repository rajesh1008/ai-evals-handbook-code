"""Chapter 6 failure injection: a new failure absorbed by a broad mode.

Plant 'payoff quoted for the borrower's other loan' in 3 payoff traces of the holdout period and
have the coder file them under FM-19, the merged payoff mode, because the symptom (a wrong payoff
figure) looks like it. Measure coverage with the inclusion test switched off and on."""
import copy
import random
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss import sampling as S
from truss import taxonomy as T
import january as J
import modes as M
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    import lab as LAB  # reuses the lab's frame, holdout and v0.2

print("######## INJECTION: payoff quoted for the borrower's other loan ########")
rng = random.Random(J.SEED + 99)
hold = [copy.deepcopy(r) for r in LAB.hrows]
clean_payoff = [r for r in hold if r["flow"] == "payoff_letter" and not r["cause"]]
planted = rng.sample(clean_payoff, 3)
for r in planted:
    r["cause"], r["note"] = "P_otherloan", "payoff figure wrong, quote was for borrower's other loan"
t02 = LAB.t02
labels = []
for r in hold:
    if not r["cause"]:
        continue
    c = "FM-19" if r["cause"] == "P_otherloan" else J.first_coder(r, t02.version)
    labels.append({"trace_id": r["trace_id"], "cause": r["cause"], "code": c,
                   "fit": LAB.fits(c, r, t02), "note": r["note"]})
no_test = [dict(l, fit=bool(l["code"])) for l in labels]
a, b = T.coverage(no_test), T.coverage(labels)
print(f"planted {len(planted)}: {[r['trace_id'] for r in planted]}")
print(f"FM-19 labels now {sum(1 for l in labels if l['code'] == 'FM-19')} (was {LAB.R['per_code_hold'].get('FM-19', 0)})")
print(f"coverage without inclusion tests: naive {a['naive']:.1%}, 'fitted' {a['fitted_share']:.1%} -> nothing flags")
print(f"coverage with the FM-19 inclusion test: fitted {b['fitted']}/{b['failing']} = {b['fitted_share']:.1%} "
      f"(Wilson {b['fitted_ci'][0]:.1%} to {b['fitted_ci'][1]:.1%})")
flag = [l["trace_id"] for l in labels if l["code"] == "FM-19" and not l["fit"]]
print(f"flagged for review (label fails its test): {len(flag)} {flag}")
cl = T.clusters([l["note"] for l in labels if l["code"] == "FM-19"])
print(f"FM-19 note clusters: {[len(g) for g in cl]}")
d = T.drift({"FM-19": (LAB.R['per_code_v02'].get('FM-19', 0), LAB.R['sample']['flows']['payoff_letter'])},
            {"FM-19": (sum(1 for l in labels if l['code'] == 'FM-19'), sum(1 for r in hold if r['flow'] == 'payoff_letter'))})[0]
print(f"rate test alone on FM-19: {d['before']} -> {d['after']}, one-sided p {d['p_up']:.4f} {d['flag'] or '(no flag)'}")
