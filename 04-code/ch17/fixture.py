"""Chapter 17 fixture (SIMULATED pairs, planted gold): 200 fee-explanation pairs
drawn from the kinds Chapter 8 and Chapter 16 use.

Everything here is deterministic (seed 2026). Pair IDs are p-0001 to p-0200.
No new production traces are added; Chapter 16's next production trace ID is
untouched. Gold is planted from the kind, not read from reply text.

Policy, fee-schedule-2026-03: $25 late fee when a payment posts more than 15
days after the due date; one courtesy waiver in any twelve months for borrowers
on autopay, applied without a call.

Each pair has two replies to the same borrower question. Gold names the better
reply (A, B or tie). Quality gap is large (a clearly wrong reply vs a clearly
right one), close (a hedged wrong reply vs a curt right one) or tied (two right
replies of different length).
"""
import random

SEED = 2026
N = 200
FAMILIES = ("S", "L", "X")  # small same-family, larger same-family, other-family

# Kind of each side: right replies are acceptable under MC-02 v1.1; wrong ones fail.
RIGHT = ("right_no", "right_waive", "defer_review")
WRONG = ("F_waive", "F_hedge", "X_wrongloan", "X_invent")

# Composition (sums to 200).
PLAN = (
    # (n, gap, lang, gold_rule)
    (110, "large", "en", "better"),
    (30,  "close", "en", "better"),
    (20,  "tied",  "en", "tie"),
    (20,  "large", "es", "better"),
    (10,  "close", "es", "better"),
    (10,  "tied",  "es", "tie"),
)


def _length(g, kind, gap):
    base = {"right_no": 88, "right_waive": 102, "defer_review": 76,
            "F_waive": 94, "F_hedge": 118, "X_wrongloan": 90, "X_invent": 84}[kind]
    jitter = g.randint(-12, 16)
    if gap == "tied":
        return max(40, base + jitter)
    return max(40, base + jitter)


def _sides(g, gap, gold_rule):
    if gold_rule == "tie":
        a, b = g.choice(RIGHT), g.choice(RIGHT)
        return a, b, "tie"
    if gap == "close":
        right, wrong = g.choice(("right_no", "right_waive")), "F_hedge"
    else:
        right, wrong = g.choice(RIGHT), g.choice(WRONG)
    if g.random() < 0.5:
        return right, wrong, "A"
    return wrong, right, "B"


def pairs(n=N, seed=SEED):
    g = random.Random(seed)
    out = []
    i = 1
    for count, gap, lang, gold_rule in PLAN:
        for _ in range(count):
            ka, kb, gold = _sides(g, gap, gold_rule)
            la, lb = _length(g, ka, gap), _length(g, kb, gap)
            if gold_rule == "tie":
                # Guarantee a length gap so a verbosity test has something to pull on.
                if la == lb:
                    la += 20
                if g.random() < 0.5:
                    la, lb = max(la, lb), min(la, lb)
                else:
                    la, lb = min(la, lb), max(la, lb)
            ga, gb = g.choice(FAMILIES), g.choice(FAMILIES)
            pid = f"p-{i:04d}"
            out.append({
                "pair_id": pid, "gap": gap, "lang": lang, "gold": gold,
                "kind_A": ka, "kind_B": kb, "len_A": la, "len_B": lb,
                "gen_A": ga, "gen_B": gb,
                "quality_matched": gold_rule == "tie",
                # A 30% pad, as whole words of courtesy filler (no new facts).
                "len_A_pad": int(round(la * 1.30)),
                "len_B_pad": int(round(lb * 1.30)),
            })
            i += 1
    assert len(out) == n
    return out


def describe(ps=None):
    ps = ps or pairs()
    from collections import Counter
    return {
        "n": len(ps),
        "first": ps[0]["pair_id"], "last": ps[-1]["pair_id"],
        "gap": dict(Counter(p["gap"] for p in ps)),
        "lang": dict(Counter(p["lang"] for p in ps)),
        "gold": dict(Counter(p["gold"] for p in ps)),
        "tied": sum(p["quality_matched"] for p in ps),
        "mixed_family": sum(p["gen_A"] != p["gen_B"] for p in ps),
    }


if __name__ == "__main__":
    print(describe())
