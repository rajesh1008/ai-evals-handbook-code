"""Try it yourself 1: how the flip rate moves with temperature."""
from replay import flipped, open_store, pass_hat_k, pick_conversations, replay

convs = pick_conversations(open_store())
for temp in (0.0, 0.3, 0.7, 1.0):
    res = replay(convs, runs=3, temperature=temp)
    print(f"temperature {temp}: flipped {len(flipped(res)):2d} of 20, "
          f"pass^3 = {pass_hat_k(res, 3):.0%}")
