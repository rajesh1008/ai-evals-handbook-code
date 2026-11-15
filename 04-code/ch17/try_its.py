"""Three Try It Yourself variations. SIMULATED. Writes out/tryits.json."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import pairs
from judges import orig_run, slot_run, pick, JUDGES
from truss.bias import (
    position_calls, position_summary, flip_summary, majority, correlated_errors,
)

PS = pairs()
OUT = {}


def head(s):
    print("\n" + "=" * 80 + "\n" + s + "\n" + "=" * 80)


head("Try It 1. Pad reply A by 50% instead of 30% (J-S)")
# 50% pad: temporarily rewrite lengths
ps50 = []
for p in PS:
    q = dict(p)
    q["len_A_pad"] = int(round(p["len_A"] * 1.50))
    ps50.append(q)
base = orig_run("S", PS)
pad30 = orig_run("S", PS, pad="A")
pad50 = orig_run("S", ps50, pad="A")
f30 = flip_summary(base, pad30, toward=["A"] * len(PS))
f50 = flip_summary(base, pad50, toward=["A"] * len(PS))
print(f"30% pad: flipped {f30['flipped']}/{f30['n']} = {f30['flip_rate']:.1%}; "
      f"toward A {f30['toward']}/{f30['flipped']} = {f30['toward_rate']:.1%}")
print(f"50% pad: flipped {f50['flipped']}/{f50['n']} = {f50['flip_rate']:.1%}; "
      f"toward A {f50['toward']}/{f50['flipped']} = {f50['toward_rate']:.1%}")
OUT["pad"] = {"f30": f30, "f50": f50}


head("Try It 2. Position rate after dropping large-gap pairs (all three judges)")
for j in ("S", "L", "X"):
    first = slot_run(j, PS, swap=False)
    swapped = slot_run(j, PS, swap=True)
    calls = position_calls(first, swapped)
    idx = [i for i, p in enumerate(PS) if p["gap"] != "large"]
    sub = position_summary([calls[i] for i in idx])
    all_ = position_summary(calls)
    print(f"J-{j}: all pairs {all_['position']}/{all_['parsed']} = {all_['position_rate']:.1%}; "
          f"close+tied only {sub['position']}/{sub['parsed']} = {sub['position_rate']:.1%}")
    OUT.setdefault("close_tied", {})[j] = {"all": all_["position_rate"],
                                           "close_tied": sub["position_rate"],
                                           "n": sub["parsed"], "pos": sub["position"]}


head("Try It 3. Majority of same-family (S+L) vs a mixed pair (S+X) vs all three")
picks = {j: orig_run(j, PS) for j in ("S", "L", "X")}
gold = [p["gold"] for p in PS]
# Two-judge majority needs a tie-breaker: if they disagree, call it tie.
def acc(pred):
    scored = [(a, g) for a, g in zip(pred, gold) if g != "tie"]
    return sum(a == g for a, g in scored), len(scored)

maj3 = majority([picks["S"], picks["L"], picks["X"]])
# same-family two-judge: agree or tie
maj_sl = [a if a == b else "tie" for a, b in zip(picks["S"], picks["L"])]
maj_sx = [a if a == b else "tie" for a, b in zip(picks["S"], picks["X"])]
print("accuracy on pairs with a better reply:")
for name, pred in (("J-S", picks["S"]), ("J-L", picks["L"]), ("J-X", picks["X"]),
                   ("majority of three", maj3),
                   ("S+L agree-or-tie", maj_sl),
                   ("S+X agree-or-tie", maj_sx)):
    k, n = acc(pred)
    print(f"  {name:22s} {k}/{n} = {k/n:.1%}")
    OUT.setdefault("panel", {})[name] = {"k": k, "n": n, "rate": k / n}
c_sl = correlated_errors(picks["S"], picks["L"], gold)
c_sx = correlated_errors(picks["S"], picks["X"], gold)
print(f"shared-mistake ratio S-L {c_sl['ratio']:.2f} (both {c_sl['both']}); "
      f"S-X {c_sx['ratio']:.2f} (both {c_sx['both']})")
OUT["corr_SL"] = c_sl
OUT["corr_SX"] = c_sx

# strip 'where' lists which can be long
def slim(f):
    return {k: v for k, v in f.items() if k != "where"}
OUT["pad"] = {"f30": slim(f30), "f50": slim(f50)}

(HERE / "out" / "tryits.json").write_text(json.dumps(OUT, indent=2, default=float))
print("\nWrote out/tryits.json")
