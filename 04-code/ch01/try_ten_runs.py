"""Try it yourself 2: ten runs, and how pass@k and pass^k pull apart."""
from replay import (flipped, open_store, pass_at_k, pass_hat_k, pass_rate,
                    pick_conversations, replay)

convs = pick_conversations(open_store())
res = replay(convs, runs=10, temperature=0.7)
print("single-run pass counts:", [pass_rate(res, r)[0] for r in range(1, 11)])
print("flipped across ten runs:", len(flipped(res)), "of 20")
for k in (1, 2, 3, 5, 10):
    print(f"k={k:2d}  pass@k = {pass_at_k(res, k):.0%}  pass^k = {pass_hat_k(res, k):.0%}")
