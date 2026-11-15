"""Chapter 8: how many traces a week does a monitor card need before its alert means anything?
For each monitor card: the mode's rate in its flow over 1 to 14 March (fixture truth), the weekly
volume, and for weekly samples of 50, 100 and 200 and a census, the chance the weekly rate is
above the card's alert (a) when nothing has changed and (b) when the mode's rate has doubled.
Exact binomial tails; no simulation."""
import sys
from math import comb
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import march as MAR  # noqa: E402
import suite as SU   # noqa: E402

def above(n, p, a):
    """P(X/n > a) for X ~ Binomial(n, p)."""
    k0 = int(a * n) + 1
    return sum(comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(k0, n + 1)) if p > 0 else 0.0


def tail(n, p, a):
    # exact for small n; normal approximation with continuity correction for a census
    if n <= 400:
        return above(n, p, a)
    from math import erf, sqrt
    mu, sd = n * p, sqrt(n * p * (1 - p))
    z = (int(a * n) + 0.5 - mu) / sd
    return 0.5 * (1 - erf(z / sqrt(2)))


def best_alert(n, p):
    """Lowest alert (in steps of 0.5 points) whose false-alert chance is at most 5% at the current rate."""
    a = p
    while tail(n, p, a) > 0.05:
        a += 0.005
    return a



def mode_rate(rows, card):
    pop = [r for r in rows if r["flow"] == card.flows[0]]
    return sum(1 for r in pop if SU.CODE.get(r["cause"]) == card.modes[0]) / len(pop), len(pop) // 2


def main():
    rows = [r for r in MAR.build() if r["status"] != "abandoned"]
    cs, _, _ = SU.cards()
    print(f"{'card':<6} {'mode':<6} {'flow':<18} {'rate':>6} {'alert':>6} {'week':>5}   "
          "false alert / catches a doubling, weekly n = 50 | 100 | 200 | census")
    for c in cs:
        if c.tier != "monitor":
            continue
        p, week = mode_rate(rows, c)
        cells = [f"{tail(n, p, c.alert):.0%}/{tail(n, min(1, 2 * p), c.alert):.0%}"
                 for n in (50, 100, 200, week)]
        print(f"{c.id:<6} {c.modes[0]:<6} {c.flows[0]:<18} {p:>6.1%} {c.alert:>6.0%} {week:>5}   "
              + " | ".join(cells))

    print("\nalert set so a quiet week alerts at most 5% of the time; chance it catches a doubling")
    print(f"{'card':<6} {'rate':>6}   weekly draw of 50    four weeks pooled (200)   weekly census")
    for c in cs:
        if c.tier != "monitor":
            continue
        pop = [r for r in rows if r["flow"] == c.flows[0]]
        p = sum(1 for r in pop if SU.CODE.get(r["cause"]) == c.modes[0]) / len(pop)
        week = len(pop) // 2
        out = []
        for n in (50, 200, week):
            a = best_alert(n, p)
            out.append(f"{a:>5.1%} -> {tail(n, min(1, 2 * p), a):>4.0%}")
        print(f"{c.id:<6} {p:>6.1%}   " + "     ".join(f"{x:<20}" for x in out))


if __name__ == "__main__":
    main()
