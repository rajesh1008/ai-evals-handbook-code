"""Failure injection: a position bias that flips 9% of pairwise verdicts.

A gold-following judge (no slot preference, no noise) is consistent on every
pair. The injection forces 18 of the 200 pairs (seed 2026) to pick slot A in
both orders: exactly 9.0%. The battery must flag that rate (Harbor's flag
cut-off is 5%; fail is 10%). Dual-order mitigation drops those 18 pairs.

SIMULATED. Writes out/inject.json.
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import pairs
from truss.bias import (
    position_calls, position_summary, mitigate_position, evaluate_tests, disqualify,
)

PS = pairs()
SEED = 2026
N_FORCE = 18  # 18/200 = 9.0%


def gold_slot(pair, swap=False):
    """Slot letter for a judge that always picks the better reply (ties -> A)."""
    winner = pair["gold"] if pair["gold"] != "tie" else "A"
    if not swap:
        return winner
    return {"A": "B", "B": "A"}[winner]


def main():
    first0 = [gold_slot(p, swap=False) for p in PS]
    swapped0 = [gold_slot(p, swap=True) for p in PS]
    s0 = position_summary(position_calls(first0, swapped0))
    gold = [p["gold"] for p in PS]
    print("=" * 80)
    print("Injection: position bias at exactly 9% of pairwise verdicts")
    print("=" * 80)
    print(f"Gold-following judge (no slot preference): "
          f"{s0['position']}/{s0['parsed']} = {s0['position_rate']:.1%}")

    g = random.Random(SEED)
    forced = sorted(g.sample(range(len(PS)), N_FORCE))
    first_e, swapped_e = list(first0), list(swapped0)
    for i in forced:
        first_e[i] = "A"
        swapped_e[i] = "A"
    se = position_summary(position_calls(first_e, swapped_e))
    print(f"After forcing 18 pairs (seed 2026, {[PS[i]['pair_id'] for i in forced][:3]}...) "
          f"to pick slot A both times: {se['position']}/{se['parsed']} = "
          f"{se['position_rate']:.1%} (Wilson {se['position_ci'][0]:.1%} to "
          f"{se['position_ci'][1]:.1%})")
    if se["position"] != N_FORCE:
        raise SystemExit(f"expected {N_FORCE} position outcomes, got {se['position']}")

    mit = mitigate_position(first_e, swapped_e, gold=gold)
    print(f"Dual-order mitigation keeps {mit['n']} of 200; accuracy on kept "
          f"scored pairs {mit.get('accuracy', float('nan')):.1%} "
          f"(n={mit.get('n_scored')})")

    reversals = gold_forced = 0
    for i in forced:
        if gold[i] == "tie":
            continue
        gold_forced += 1
        if gold[i] == "B":  # first-slot-only reading picks A
            reversals += 1
    print(f"Of the 18 injected pairs, {gold_forced} have a better reply; "
          f"a first-slot-only reading would reverse {reversals} of them.")

    rows = evaluate_tests({"position_rate": se["position_rate"]})
    adm = disqualify(rows, role="pairwise")
    print(f"Battery on the injected judge (position only): {rows[0]['verdict']} "
          f"(flag {rows[0]['flag']}, fail {rows[0]['fail']}); "
          f"pairwise admit={adm['admit']} {adm['reasons'] or '—'}")

    out = {
        "baseline": {"position": s0["position"], "n": s0["parsed"],
                     "rate": s0["position_rate"]},
        "injected": {"position": se["position"], "n": se["parsed"],
                     "rate": se["position_rate"], "ci": list(se["position_ci"]),
                     "forced": [PS[i]["pair_id"] for i in forced],
                     "forced_n": N_FORCE},
        "mitigation": {k: mit[k] for k in mit if k != "kept"},
        "reversals": reversals, "gold_forced": gold_forced,
        "battery": {"verdict": rows[0]["verdict"], "admit_pairwise": adm["admit"],
                    "reasons": adm["reasons"], "flags": adm["flags"]},
    }
    (HERE / "out" / "inject.json").write_text(json.dumps(out, indent=2, default=float))
    print("Wrote out/inject.json")


if __name__ == "__main__":
    main()
