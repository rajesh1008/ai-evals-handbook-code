"""Chapter 16 Try It Yourself variations (REAL model runs, cached; SIMULATED fixture)."""
from collections import Counter

from common import TEST, BUGS, NORMAL, RES, J, agent, llm, gen, score, usage, line, verdicts

print("Try it 1: drop the critique and ask for the verdict alone (same rules, same 200 test traces)")
a = score("test_v1_small_r0", TEST); b = score("test_verdict_only", TEST)
print(line("critique first", a)); print(line("verdict only", b))
ua, ub = usage(RES["test_v1_small_r0"].values()), usage(RES["test_verdict_only"].values())
print(f"  tokens out per call {ua['out_per']:.0f} against {ub['out_per']:.0f}; cost per call ${ua['per_call']:.5f} against ${ub['per_call']:.5f}; "
      f"latency p50 {ua['p50']:.2f} s against {ub['p50']:.2f} s")
T = {t["trace_id"]: t for t in TEST}
print("  verdict-only disagreements:", [(i, T[i]["kind"], p) for i, p in b["pred"].items() if p != T[i]["v11"]])

print("\nTry it 2: the same judge on Spanish replies (100 test traces translated by the small model; prompt in English)")
S = gen.spanish(); ids = [t for t in TEST if t["trace_id"] in S]
es = score("test_v1_spanish", ids)
en = score("test_v1_small_r0", ids)
print(line("English replies, same 100", en)); print(line("Spanish replies", es))
print("  Spanish disagreements:", [(i, T[i]["kind"], p) for i, p in es["pred"].items() if p != T[i]["v11"]])
print("  English disagreements on the same 100:", [(i, T[i]["kind"], p) for i, p in en["pred"].items() if p != T[i]["v11"]])

print("\nTry it 3: give the agent judge a date calculator (days_between) and rerun the small agent")
for calc, label in ((False, "agent small"), (True, "agent small + days_between")):
    d = agent.run(llm.SMALL, calc=calc)
    caught = sum(J.verdict(d[t["trace_id"]]["text"]) == "fail" for t in BUGS)
    nw = [(t["trace_id"], t["kind"]) for t in NORMAL if J.verdict(d[t["trace_id"]]["text"]) != t["truth"]]
    used = sum(any(c["name"] == "days_between" for c in r["tool_calls"]) for r in d.values())
    u = usage(d.values())
    print(f"  {label:28s} bug traces caught {caught}/20; wrong on other 40: {len(nw)} {nw}; traces that used days_between {used}; "
          f"cost per trace ${u['per_call']:.4f}")
