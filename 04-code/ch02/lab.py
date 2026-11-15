"""Chapter 2 Lab: a first honest evaluation of Compass, end to end."""
import csv
import io
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss.complete import completeness  # noqa: E402
from truss.label import session  # noqa: E402
from truss.rates import upper_bound, traces_needed, weighted_rate, wilson  # noqa: E402
from truss.report import notes_by_flow, per_flow, rare_failure_line, table  # noqa: E402
from truss.store import open_store  # noqa: E402
from pilot_detail import ORDER, QUOTAS, SEED, first_pass_labels, first_pass_sample, trace_view  # noqa: E402

OUT = HERE / "out"


def shares(db):
    rows = dict(db.execute("SELECT flow, COUNT(*) FROM traces GROUP BY flow"))
    total = sum(rows.values())
    return {f: n / total for f, n in rows.items()}, rows


def step1_sheet(db):
    print("== 1. Ryan's sheet against the pilot ==")
    sh, counts = shares(db)
    sheet = dict(db.execute("SELECT flow, COUNT(*) FROM traces JOIN ryan_sheet USING(trace_id) GROUP BY flow"))
    turns = db.execute("SELECT AVG(turns) FROM traces JOIN ryan_sheet USING(trace_id)").fetchone()[0]
    for f in ORDER:
        print(f"{f:<18} sheet {sheet.get(f, 0):>2}/40 ({sheet.get(f, 0) / 40:5.1%})   pilot {sh[f]:5.1%}")
    print(f"mean turns: sheet {turns:.1f}, pilot "
          f"{db.execute('SELECT AVG(turns) FROM traces').fetchone()[0]:.2f}")
    print(f"0 failures in 40: one-sided 95% upper bound {upper_bound(0, 40):.1%}")
    print(f"0 failures in 1 hardship: upper bound {upper_bound(0, 1):.0%}")
    print(f"traces_needed(0.005) = {traces_needed(0.005)}")
    for k in (0, 1, 2):
        lo, hi = wilson(k, 100)
        print(f"{k} failure{"" if k == 1 else "s"} in 100: one-sided 95% bound {upper_bound(k, 100):.1%}; "
              f"two-sided Wilson 95% {lo:.1%} to {hi:.1%}")
    return sheet


def step2_sample(db):
    print("\n== 2. The stratified sample ==")
    sh, counts = shares(db)
    sample = first_pass_sample(db)
    prop = {f: round(300 * sh[f]) for f in ORDER}
    for f in ORDER:
        print(f"{f:<18} pilot {counts[f]:>5}  proportional {prop[f]:>3}  quota {QUOTAS[f]:>3}  "
              f"hardship-style bound at quota: {upper_bound(0, QUOTAS[f]):.1%}")
    print(len(sample), sample[:3])
    q = ",".join("?" * len(sample))
    tiers = db.execute(f"SELECT risk_tier, COUNT(*) FROM traces WHERE trace_id IN ({q}) "
                       "GROUP BY risk_tier ORDER BY risk_tier", sample).fetchall()
    print("risk tiers in sample:", ", ".join(f"{t} {n}" for t, n in tiers))
    for col in ("channel",):
        got = dict(db.execute(f"SELECT {col}, COUNT(*) FROM traces WHERE trace_id IN ({q}) GROUP BY 1", sample))
        print(f"{col} in sample: " + ", ".join(f"{k} {v}" for k, v in sorted(got.items())))
    weeks = db.execute(f"SELECT (julianday(started_at) - julianday('2026-09-07')) / 7 AS w FROM traces "
                       f"WHERE trace_id IN ({q})", sample).fetchall()
    per_week = [sum(int(w[0]) == i for w in weeks) for i in range(6)]
    from scipy.stats import chisquare
    print("pilot weeks 1-6 in sample:", per_week,
          f"chi-square p = {chisquare(per_week).pvalue:.3f} (pilot traffic was flat by week)")
    return sample, sh, prop


def step3_complete(db, sample):
    print("\n== 3. Completeness check before labelling ==")
    ok, bad = completeness([trace_view(db, t) for t in sample])
    print(f"complete {len(ok)}, incomplete {len(bad)}")


def step4_label(db, sample, labels):
    print("\n== 4. Labelling (first two hardship traces, replayed from the record) ==")
    rec = {r["trace_id"]: r for r in labels}
    hard = [t for t in sample if rec[t]["flow"] == "hardship"]
    hard = [hard[0], next(t for t in hard if rec[t]["note"].startswith("offer drafted"))]
    answers = iter(f"{'p' if rec[t]['verdict'] == 'pass' else 'f ' + rec[t]['note']}" for t in hard)
    path = OUT / "demo_labels.csv"
    path.unlink(missing_ok=True)
    session([trace_view(db, t, note=rec[t]["note"]) for t in hard], path, "Grace Holloway", answers)
    for line in path.read_text().splitlines()[1:]:
        print(line.rsplit(",", 1)[0])


def step5_report(db, labels, sh):
    print("\n== 5. First report ==")
    print(table(labels, sh, ORDER))
    print("\nfailure notes:")
    for f, c in notes_by_flow(labels).items():
        for note, k in c.most_common():
            print(f"  {f:<18} {k}  {note}")
    hard = [trace_view(db, r["trace_id"]) for r in labels if r["flow"] == "hardship"]
    offers = sum(t["reached_offer"] for t in hard)
    print()
    print(rare_failure_line("wrong hardship offers per hardship conversation", 0, 100, 0.005))
    print(rare_failure_line("wrong hardship offers per drafted offer", 0, offers, 0.005))
    k, n = per_flow(labels)["fee_explanation"]
    lo, hi = wilson(n - k, n)
    print(f"wrong fee explanations: {n - k} in {n} = {(n - k) / n:.1%}, Wilson {lo:.1%} to {hi:.1%}")
    return offers


def step5b_length(db, labels):
    print("\n== 5b. Pass rate by conversation length in the sample ==")
    turns = dict(db.execute("SELECT trace_id, turns FROM traces"))
    for lo, hi, name in [(1, 2, "1-2 turns (like Ryan's 40)"), (3, 6, "3-6 turns"), (7, 99, "7+ turns")]:
        rows = [r for r in labels if lo <= turns[r["trace_id"]] <= hi]
        k = sum(r["verdict"] == "pass" for r in rows)
        print(f"{name:<28} {k:>3}/{len(rows):<3} {k / len(rows):6.1%}")


def step6_agreement(labels):
    print("\n== 6. Second reader: every hardship fail plus random passes, 20 in all ==")
    rec = {r["trace_id"]: r for r in labels if r["flow"] == "hardship"}
    fails = sorted(t for t, r in rec.items() if r["verdict"] == "fail")
    passes = sorted(t for t, r in rec.items() if r["verdict"] == "pass")
    rng = random.Random(SEED + 1)
    overlap = fails + rng.sample(passes, 20 - len(fails))
    # Ben counts income the borrower stated in the opening message as confirmed.
    disagree = [t for t in fails if rec[t]["note"] == "offer drafted before income confirmed"
                and rng.random() < 0.5]
    print(f"Ben read {len(overlap)} ({len(fails)} of Grace's fails, {20 - len(fails)} passes); "
          f"agreed on {len(overlap) - len(disagree)}; disagreed on {len(disagree)}, "
          f"all 'offer drafted before income confirmed'")
    return len(disagree), len(fails)


def step7_spot_check(labels):
    """Scripted: the evaluation lead re-reads 20 of Ryan's traces; her verdicts are recorded as given."""
    print("\n== 7. Spot check of the builder's labels ==")
    ryan = sorted(r["trace_id"] for r in labels if r["annotator"] == "Ryan Mitchell")
    picked = random.Random(SEED + 2).sample(ryan, 20)
    rec = {r["trace_id"]: r["verdict"] for r in labels}
    agree = sum(rec[t] == rec[t] for t in picked)  # second reading recorded identical verdicts
    fails = sum(rec[t] == "fail" for t in picked)
    print(f"re-read {len(picked)} of Ryan's {len(ryan)} (including {fails} of his fails); agreed on {agree}; "
          f"one-sided 95% bound on the disagreement rate: {upper_bound(0, len(picked)):.1%}")


def main():
    OUT.mkdir(exist_ok=True)
    db = open_store()
    sheet = step1_sheet(db)
    sample, sh, prop = step2_sample(db)
    step3_complete(db, sample)
    labels = first_pass_labels(db)
    with open(OUT / "first_pass_labels.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ["trace_id", "flow", "verdict", "note", "annotator"])
        w.writeheader(); w.writerows(labels)
    step4_label(db, sample, labels)
    offers = step5_report(db, labels, sh)
    step5b_length(db, labels)
    dis, fails = step6_agreement(labels)
    step7_spot_check(labels)
    rows = per_flow(labels)
    json.dump({"shares": sh, "sheet": sheet, "proportional": prop, "quotas": QUOTAS,
               "per_flow": rows, "weighted": weighted_rate(rows, sh), "offers": offers,
               "notes": {f: dict(c) for f, c in notes_by_flow(labels).items()},
               "turns_all": [r[0] for r in db.execute("SELECT turns FROM traces")],
               "turns_sheet": [r[0] for r in db.execute(
                   "SELECT turns FROM traces JOIN ryan_sheet USING(trace_id)")]},
              open(OUT / "lab.json", "w"))


if __name__ == "__main__":
    main()
