"""Chapter 2: the first month of monitoring, simulated.

Each week a fresh stratified sample of 70 live traces is labelled. Verdicts
are drawn from the per-flow failure rates measured in the first pass. Two
events are scripted and stated here: on 17 November a logging-library
upgrade drops tool calls from about 10% of traces, and in week 4 one hardship
trace carries a wrong offer (a prior deferral missed, the pilot complaint's
failure mode)."""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss.complete import missing_tools  # noqa: E402
from truss.rates import upper_bound, traces_needed, wilson  # noqa: E402
from truss.report import per_flow  # noqa: E402
from truss.store import open_store  # noqa: E402
from pilot_detail import SEED, first_pass_labels, tools_for  # noqa: E402

WEEKS = ["2-8 Nov", "9-15 Nov", "16-22 Nov", "23-29 Nov"]
WEEKLY = {"hardship": 25, "fee_explanation": 20, "account_question": 10,
          "statement_request": 5, "payoff_letter": 5, "lien_release": 5}
BUG_WEEK, OFFER_WEEK = 2, 3  # zero-based


def main():
    rows = per_flow(first_pass_labels(open_store()))
    fail_rate = {f: 1 - k / n for f, (k, n) in rows.items()}
    rng = random.Random(f"monitor|{SEED}")
    hard_n, wrong = 100, 0
    series, month = [], {f: [0, 0] for f in WEEKLY}
    print("week        labelled  pass (as read)  pass (complete only)  incomplete  hardship read  wrong offers")
    for w, name in enumerate(WEEKS):
        seen, clean, incomplete = [], [], 0
        wk = {f: [0, 0] for f in WEEKLY}
        for flow, q in WEEKLY.items():
            for i in range(q):
                v = "fail" if rng.random() < fail_rate[flow] else "pass"
                if w == OFFER_WEEK and flow == "hardship" and i == 0:
                    v = "fail"  # the scripted wrong offer
                tools = tools_for("", flow, False)
                if w == BUG_WEEK and rng.random() < 0.10:
                    tools = []
                gap = missing_tools(flow, tools)
                read = "fail" if gap else v  # annotators fail a reply with no lookup
                seen.append(read == "pass")
                if gap:
                    incomplete += 1
                else:
                    clean.append(v == "pass")
                    month[flow][0] += v == "pass"; month[flow][1] += 1
                    wk[flow][0] += v == "pass"; wk[flow][1] += 1
                    hard_n += flow == "hardship"
        wrong += w == OFFER_WEEK
        k1, n1, k2, n2 = sum(seen), len(seen), sum(clean), len(clean)
        series.append({"week": name, "k_read": k1, "n_read": n1, "k_clean": k2, "n_clean": n2,
                       "incomplete": incomplete, "hard_n": hard_n, "wrong": wrong,
                       "ci_read": wilson(k1, n1), "ci_clean": wilson(k2, n2), "by_flow": wk})
        print(f"{name:<11} {n1:>8}  {k1:>3} ({k1 / n1:5.1%})    {k2:>3}/{n2} ({k2 / n2:5.1%})"
              f"   {incomplete:>9}  {hard_n:>13}  {wrong:>12}")
    print("\nweek by flow, complete traces only (pass/read):")
    for r in series:
        print(f"  {r['week']:<10} " + "  ".join(f"{f.split('_')[0]} {k}/{n}" for f, (k, n) in r["by_flow"].items()))
    print("\nmonth, complete traces only, by flow:")
    for f, (k, n) in month.items():
        lo, hi = wilson(n - k, n)
        print(f"  {f:<18} {n - k:>2} fail in {n:<3} ({(n - k) / n:5.1%}, Wilson {lo:.1%} to {hi:.1%})")
    fk, fn = rows["fee_explanation"]; mk, mn = month["fee_explanation"]
    lo, hi = wilson(fn - fk + mn - mk, fn + mn)
    print(f"wrong fee explanations pooled with the first pass: {fn - fk + mn - mk} in {fn + mn} "
          f"({(fn - fk + mn - mk) / (fn + mn):.1%}, Wilson {lo:.1%} to {hi:.1%})")
    lo, hi = wilson(wrong, hard_n)
    print(f"wrong hardship offers, Wilson two-sided: {lo:.2%} to {hi:.1%}")
    print(f"\nwrong hardship offers: {wrong} in {hard_n}; one-sided 95% upper bound "
          f"{upper_bound(wrong, hard_n):.1%}; under 0.5% now needs {traces_needed(0.005, wrong)} "
          f"traces (was {traces_needed(0.005, 0)} at zero failures)")
    json.dump(series, open(HERE / "out" / "monitor.json", "w"))


if __name__ == "__main__":
    main()
