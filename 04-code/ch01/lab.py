"""Chapter 1 Lab, main run: 20 conversations, three runs, production temperature."""
from collections import Counter

from replay import (check_manifest, flipped, open_store, pass_at_k, pass_hat_k,
                    pass_rate, pick_conversations, replay, wilson)

db = open_store()
convs = pick_conversations(db)
print("flows in the 20:", dict(Counter(f for _, f in convs)))
results = replay(convs, runs=3)
print("temperature:", check_manifest(results))
for run in (1, 2, 3):
    k, n = pass_rate(results, run)
    lo, hi = wilson(k, n)
    print(f"run {run}: {k}/{n} pass = {k/n:.0%}  (Wilson 95%: {lo:.0%} to {hi:.0%})")
flips = flipped(results)
print(f"conversations that changed verdict: {len(flips)} of {len(results)}")
for t in flips:
    flow = dict(convs)[t]
    print("  ", t, flow, [r["verdict"] for r in results[t]],
          [r["failure_mode"] for r in results[t] if r["failure_mode"]])
print(f"pass@3 = {pass_at_k(results, 3):.0%}   pass^3 = {pass_hat_k(results, 3):.0%}")
