"""Chapter 2 Try It Yourself: three variations on the Lab."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss.gate import paired_changes  # noqa: E402
from truss.rates import upper_bound, traces_needed, weighted_rate  # noqa: E402
from truss.report import per_flow  # noqa: E402
from truss.store import open_store  # noqa: E402
from gate_run import replay_candidate  # noqa: E402
from lab import shares  # noqa: E402
from pilot_detail import ORDER, first_pass_labels  # noqa: E402


def try1_proportional(sh):
    print("== Try 1: proportional allocation of 300 ==")
    for f in ORDER:
        n = round(300 * sh[f])
        print(f"{f:<18} n={n:>3}  bound on zero failures {upper_bound(0, n):5.1%}")


def try2_sizes():
    print("\n== Try 2: traces needed for a one-sided 95% bound under the target ==")
    print("target   0 failures  1 failure  2 failures")
    for target in (0.005, 0.01, 0.02, 0.05):
        print(f"{target:>6.1%}  " + "  ".join(f"{traces_needed(target, k):>9}" for k in range(3)))


def try3_overall_only(labels, sh):
    print("\n== Try 3: gate on the traffic-weighted overall rate alone ==")
    cand = replay_candidate(labels)
    b = per_flow(labels)
    c = per_flow([{"flow": f, "verdict": v} for f, v in cand.values()])
    wb, wc = weighted_rate(b, sh), weighted_rate(c, sh)
    print(f"baseline {wb:.1%}, candidate {wc:.1%}: "
          f"{'SHIP' if wc >= wb else 'HOLD'} under an overall-only rule")
    base = {r['trace_id']: (r['flow'], r['verdict']) for r in labels}
    print(f"hardship traces newly failing, unseen by that rule: "
          f"{paired_changes(base, cand)['hardship'][0]}")


if __name__ == "__main__":
    db = open_store()
    sh, _ = shares(db)
    try1_proportional(sh)
    try2_sizes()
    try3_overall_only(first_pass_labels(db), sh)
