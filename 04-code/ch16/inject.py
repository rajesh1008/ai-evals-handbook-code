"""Chapter 16 failure injection (REAL model run over the SIMULATED fixture): a rubric that lets the judge
grade the tone of the reply instead of its correctness. Same 200 test traces, same small model."""
from collections import Counter

from common import TEST, RES, J, score, usage, line, verdicts

print("Failure injection: the tone rubric ('clear, polite, empathetic and helpful')")
good = score("test_v1_small_r0", TEST); bad = score("test_tone", TEST)
print(line("judge v1 (facts)", good))
print(line("tone rubric", bad))
tv = verdicts("test_tone"); fv = verdicts("test_v1_small_r0")
print("\nfail verdicts by the reply's tone (tone was assigned at random, independent of correctness):")
for tone in ("warm", "curt"):
    ts = [t for t in TEST if t["tone"] == tone]
    for lab in ("pass", "fail"):
        g = [t for t in ts if t["v11"] == lab]
        print(f"  {tone:4s} replies, v1.1 label {lab}: n={len(g):3d}  tone rubric fail {sum(tv[t['trace_id']] == 'fail' for t in g):3d}  "
              f"facts judge fail {sum(fv[t['trace_id']] == 'fail' for t in g):3d}")
warm_wrong = [t for t in TEST if t["tone"] == "warm" and t["v11"] == "fail"]
print(f"\nwarm and wrong replies the tone rubric passed: {sum(tv[t['trace_id']] == 'pass' for t in warm_wrong)} of {len(warm_wrong)}")
curt_right = [t for t in TEST if t["tone"] == "curt" and t["v11"] == "pass"]
print(f"curt and right replies the tone rubric failed: {sum(tv[t['trace_id']] == 'fail' for t in curt_right)} of {len(curt_right)}")
print("by kind:", {k: dict(v) for k, v in sorted(bad["by_kind"].items())})
warm_right_fail = [t for t in TEST if t["tone"] == "warm" and t["v11"] == "pass" and tv[t["trace_id"]] == "fail"]
print(f"warm and right replies the tone rubric failed: {len(warm_right_fail)} of {sum(1 for t in TEST if t['tone']=='warm' and t['v11']=='pass')}")
ex = warm_right_fail[0]
print(f"\nexample {ex['trace_id']} ({ex['kind']}, warm, v1.1 pass): tone rubric critique, last 400 characters:")
print(RES["test_tone"][ex["trace_id"]]["text"][-400:])
u = usage(RES["test_tone"].values())
print(f"\ncost of the injected run: {u['calls']} calls ${u['cost']:.3f}")
