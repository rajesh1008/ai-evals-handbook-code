"""Chapter 4 Lab: tag every check with a layer, run the suite by layer with
timings and cost, find the layer that would have caught each defect."""
import json
import sys
import time

import harbor as H
import suite as SU
from truss.layers import LAYERS, lint, monthly_bill, summarise

H.OUT.mkdir(exist_ok=True)


def money(x):
    return f"${x:,.2f}" if x < 100 else f"${x:,.0f}"


def main():
    con = H.store()
    tok = H.tokens_by_flow(con)
    S = SU.build(tok)
    hids = SU.hardship_ids(con)
    record = {}

    print("== A. Every check, tagged ==")
    for layer, checks in S.by_layer().items():
        print(f"layer {layer}  {LAYERS[layer]}: {len(checks)} checks")
        for c in checks:
            print(f"   {c.name:<58} {c.stream:<16} {','.join(c.stages):<29} {c.owner}")
    before = {1: 3, 2: 0, 3: 3, 4: 0, 5: 2}     # Ryan's three unit tests; Gate v0; monitoring + complaints
    print("checks per layer before this chapter:", before)
    print("checks per layer now:               ", {k: len(v) for k, v in S.by_layer().items()})
    print("placement problems:", lint(S) or "none")

    print("\n== B. First run, pilot state (2024 fee schedule still in the policy folder) ==")
    ctx = SU.ctx_for((), con)
    ctx["hardship_ids"] = hids
    for stage in ("commit", "pull_request", "release"):
        t0 = time.perf_counter()
        res = S.run(stage, ctx, fail_fast=True)
        wall = time.perf_counter() - t0
        failed = [r for r in res if r.failures]
        print(f"{stage:<13} ran {len(res):>2} checks in {wall:5.2f} s; "
              f"{'HOLD at layer ' + str(failed[0].check.layer) + ': ' + failed[0].check.name + ' (' + failed[0].detail + ')' if failed else 'pass'}")
    wk = S.run("weekly", ctx, fail_fast=False)
    for r in wk:
        print(f"weekly        {r.check.name:<58} {r.failures:>4} of {r.items:>5} {r.detail}")

    print("\n== C. The three fee complaints: which layer would have caught them ==")
    tr = H.truth()
    fee_c = [t for t in tr["complaints"] if t in set(r[0] for r in con.execute(
        "SELECT trace_id FROM traces WHERE flow='fee_explanation'"))]
    hits = set(ctx["retired_hits"])
    for t in fee_c:
        print(f"  {t}  mode: {tr['mode'][t]:<44} retrieved a retired document: {t in hits}")
    fee_total = con.execute("SELECT COUNT(*) FROM traces WHERE flow='fee_explanation'").fetchone()[0]
    print(f"  pilot fee traces that retrieved fee-schedule-2024-01: {len(hits)} of {fee_total} "
          f"({len(hits) / fee_total:.1%})")
    first = min(con.execute("SELECT started_at_utc FROM traces WHERE trace_id IN (%s)" % ",".join("?" * len(hits)),
                            sorted(hits)).fetchall())[0]
    print(f"  first such trace: {first[:10]}")
    cost_l1 = S.checks[[c.name for c in S.checks].index("no retired document in the policy index")].cost.dollars(6, H.PRICES)
    print(f"  layer 1 index check: 6 documents, cost {money(cost_l1)}; fails on 'fee-schedule-2024-01'")
    print("  layer 3 reading (Chapter 2): found the ten-day grace in 4 of 70 fee traces, inside an $1,850 reading")
    lag = [(H.dt(o) - H.dt(s)).days for o, s in con.execute(
        "SELECT o.occurred_at_utc, t.started_at_utc FROM outcomes o JOIN traces t ON t.borrower_token=o.borrower_token "
        "WHERE o.kind='complaint' AND t.trace_id IN (%s)" % ",".join("?" * len(fee_c)), fee_c)]
    print(f"  layer 5 complaints: arrived {min(lag)} to {max(lag)} days after the conversation")
    cleaned = SU.ctx_for(("corpus_cleaned",), con)
    cleaned["hardship_ids"] = hids
    r = S.run("commit", cleaned)
    print(f"  after the policy team removes the 2024 schedule: commit stage "
          f"{'pass' if not any(x.failures for x in r) else 'hold'} ({len(r)} checks)")
    print("\n== D. Cost per release, by layer (stated prices; illustrative) ==")
    res = S.run("release", cleaned, fail_fast=False)
    summ = summarise(res)
    for layer in sorted(LAYERS):
        if layer in summ:
            s = summ[layer]
            print(f"layer {layer}: {s['checks']:>2} checks, {s['items']:>5} items, {s['seconds']:6.2f} s wall, {money(s['dollars']):>9}")
    sh = S.run("shadow", cleaned, fail_fast=False)
    wk = S.run("weekly", cleaned, fail_fast=False)
    sh_d, wk_d = sum(r.dollars for r in sh), sum(r.dollars for r in wk)
    rel_total = sum(s["dollars"] for s in summ.values())
    l3 = summ[3]["dollars"]
    l3_people = 100 * 10 / 60 * H.OFFICER_RATE + 200 * 3 / 60 * H.LEAD_RATE
    print(f"release total {money(rel_total)}; of which people reading {money(l3_people)} "
          f"({l3_people / rel_total:.1%}) and replay tokens {money(l3 - l3_people)}")
    print(f"layer 5: shadow week at full volume {money(sh_d)} ({5700 * 7:,} conversations at "
          f"{money(S.mean_conv)} each); weekly monitoring {money(wk_d)}")
    items = {c.name: 0 for c in S.checks}
    for r in res + sh + wk + S.run("commit", cleaned) + S.run("pull_request", cleaned):
        items[r.check.name] = r.items
    bill = monthly_bill(S, H.RUNS_PER_MONTH, items)
    print("a month at", {k: v for k, v in H.RUNS_PER_MONTH.items()}, "runs:")
    for layer, d in bill.items():
        print(f"  layer {layer}: {money(d):>9}")
    print(f"  total {money(sum(bill.values()))}")
    record.update(release=rel_total, people=l3_people, shadow=sh_d, weekly=wk_d,
                  by_layer={k: v["dollars"] for k, v in summ.items()}, month=bill)

    print("\n== E. One defect per layer: where is it caught first? ==")
    defects = [("grace_off_by_one", "fee rule charges at exactly 15 days"),
               ("router_extension_fee", "router prompt sends 'extension' and 'skip' to fees"),
               ("offer_before_income", "prompt drafts offers before income is confirmed"),
               ("reask_on_range", "Compass re-asks when income is given as a range"),
               ("reranker_slow", "new reranker adds 1.8 s to retrieval turns")]
    rows = []
    for d, what in defects:
        c = SU.ctx_for(("corpus_cleaned", d), con)
        c["hardship_ids"] = hids
        out = S.run("release", c, fail_fast=False) + S.run("shadow", c, fail_fast=False)
        caught = sorted({r.check.layer for r in out if r.failures})
        names = [f"{r.check.name} ({r.detail})" if r.detail else r.check.name for r in out if r.failures]
        first = caught[0] if caught else None
        spent = sum(r.dollars for r in out if r.check.layer <= (first or 5))
        rows.append((d, first, spent))
        print(f"{d:<21} {what:<52} first caught at layer {first}; also {caught[1:] or '-'}")
        print(f"{'':<21} by: {names[0]}")
        print(f"{'':<21} spent to reach that layer: {money(spent)}")
    fee70 = [t for t, _ in cleaned["sample"] if t in set(x for x, in con.execute(
        "SELECT trace_id FROM traces WHERE flow='fee_explanation'"))]
    at15 = sum(json.loads(a)["result"]["days_late"] == 15 for a, in con.execute(
        "SELECT attrs FROM spans WHERE name='execute_tool get_fee_schedule' AND trace_id IN (%s)"
        % ",".join("?" * len(fee70)), fee70))
    print(f"grace_off_by_one at layer 3 instead: sampled fee traces exactly 15 days late: {at15} of {len(fee70)}")
    record["defects"] = rows

    print("\n== F. Which layer can catch each failure mode (lowest layer that sees it) ==")
    LOWEST = {
        "ten-day grace period quoted (policy is 15)": (1, "index check: retired document still retrievable"),
        "second deferral within 12 months offered": (1, "rule on the account history the tool returned"),
        "offer sent without saying a loan officer must approve it": (1, "fixed disclosure sentence present when draft_offer ran"),
        "per diem interest omitted": (1, "payoff arithmetic on the quote the letter used"),
        "wrong good-through date": (1, "date arithmetic on the quote"),
        "wrong balance date": (2, "extract the date the reply states, compare with the tool's"),
        "wrong title state": (2, "extract the state the reply names, compare with get_title_status"),
        "wrong statement period": (2, "extract the period requested, compare with send_statement"),
        "offer drafted before income confirmed": (3, "whether income was confirmed is a reading"),
        "fee not waived when policy says waive": (3, "which waiver applies is a reading of policy and history"),
        "missed borrower's second loan": (3, "whether the reply should have raised it is a reading"),
        "no hand-off when borrower asked for a person": (3, "the request is phrased a hundred ways; L4 for long conversations"),
        "release promised before title office date": (3, "the promise is a reading; the real lag is a layer-five outcome"),
    }
    from collections import Counter
    modes = Counter(tr["mode"][t] for t, f in tr["fail"].items() if f and t in tr["mode"])
    by_layer = Counter()
    for m, n in modes.most_common():
        layer, why = LOWEST[m]
        by_layer[layer] += n
        print(f"  L{layer}  {m:<58} {n:>4}  {why}")
    tot = sum(modes.values())
    print(f"planted failing traces with a named mode: {tot}; by lowest layer: " +
          ", ".join(f"L{k} {v} ({v / tot:.0%})" for k, v in sorted(by_layer.items())))
    print(f"modes by lowest layer: " + ", ".join(f"L{k} {sum(1 for v in LOWEST.values() if v[0] == k)}" for k in (1, 2, 3)))
    record["modes"] = {m: [LOWEST[m][0], n] for m, n in modes.items()}
    record["mode_layers"] = dict(by_layer)
    json.dump(record, open(H.OUT / "lab.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
