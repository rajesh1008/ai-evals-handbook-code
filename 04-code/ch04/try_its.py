"""Chapter 4 Try It Yourself: three variations on the Lab."""
import harbor as H
import suite as SU
from truss.layers import LAYERS, Cost, lint, monthly_bill


def money(x):
    return f"${x:,.3f}" if x < 1 else f"${x:,.2f}" if x < 100 else f"${x:,.0f}"


def items_for(S, ctx):
    items = {}
    for st in ("commit", "pull_request", "release", "shadow", "weekly"):
        for r in S.run(st, ctx, fail_fast=False):
            items[r.check.name] = r.items
    return items


def main():
    con = H.store()
    tok = H.tokens_by_flow(con)
    hids = SU.hardship_ids(con)
    ctx = SU.ctx_for(("corpus_cleaned",), con)
    ctx["hardship_ids"] = hids

    print("== Try 1: add a check of your own and place it ==")
    S = SU.build(tok)

    @S.check("payoff quote adds per diem interest", 1, "code tests", "Ryan (engineering)",
             ("commit", "pull_request", "release"), Cost(cpu_seconds=0.01))
    def _(c):
        cases = [(10_000.00, 1.37, 12, 10_016.44), (2_500.00, 0.41, 0, 2_500.00)]
        bad = [x for x in cases if round(x[0] + x[1] * x[2], 2) != x[3]]
        return len(cases), len(bad), ""
    print("added at layer 1; lint:", lint(S) or "none")
    S.add(SU.Check("payoff letters read for per diem", 3, "human review", "evaluation lead", ("commit",),
                   lambda c: (35, 0, ""), Cost(human_minutes=3, human_rate=H.LEAD_RATE)))
    print("the same failure checked by reading, placed at commit; lint:")
    for p in lint(S):
        print("  ", p)

    print("\n== Try 2: change how often each stage runs ==")
    S = SU.build(tok)
    items = items_for(S, ctx)
    for label, runs in [("today", H.RUNS_PER_MONTH),
                        ("weekly releases", {**H.RUNS_PER_MONTH, "release": 4.33}),
                        ("weekly releases, twice the commits", {**H.RUNS_PER_MONTH, "release": 4.33, "commit": 240})]:
        bill = monthly_bill(S, runs, items)
        print(f"{label:<36} " + "  ".join(f"L{k} {money(v):>8}" for k, v in bill.items())
              + f"   total {money(sum(bill.values()))}")

    print("\n== Try 3: delete layer two and inject the router defect ==")
    for keep_l2 in (True, False):
        S = SU.build(tok)
        if not keep_l2:
            S.checks = [c for c in S.checks if c.layer != 2]
        c = SU.ctx_for(("corpus_cleaned", "router_extension_fee"), con)
        c["hardship_ids"] = hids
        res = S.run("release", c, fail_fast=True)
        fail = [r for r in res if r.failures]
        spent = sum(r.dollars for r in res)
        print(f"layer 2 {'kept   ' if keep_l2 else 'deleted'}: caught at layer {fail[0].check.layer} by "
              f"'{fail[0].check.name}' ({fail[0].detail}); spent {money(spent)} with fail-fast")


if __name__ == "__main__":
    main()
