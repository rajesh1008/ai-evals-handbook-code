"""Chapter 2: the first report. Per-flow rates first, the overall number last."""
from collections import Counter, defaultdict

from truss.rates import upper_bound, traces_needed, weighted_rate, wilson


def per_flow(labels):
    """{flow: (passes, labelled)} from label rows; 'cannot tell' rows are counted apart."""
    k, n = Counter(), Counter()
    for r in labels:
        if r["verdict"] == "cannot_tell":
            continue
        n[r["flow"]] += 1
        k[r["flow"]] += r["verdict"] == "pass"
    return {f: (k[f], n[f]) for f in n}


def notes_by_flow(labels):
    out = defaultdict(Counter)
    for r in labels:
        if r["verdict"] == "fail":
            out[r["flow"]][r["note"]] += 1
    return out


def table(labels, shares, order):
    rows = per_flow(labels)
    lines = ["flow               pass/n    rate   Wilson 95%      traffic share"]
    for f in order:
        k, n = rows[f]
        lo, hi = wilson(k, n)
        lines.append(f"{f:<18} {k:>3}/{n:<4} {k / n:6.1%}  {lo:5.1%} to {hi:5.1%}   {shares[f]:5.1%}")
    k = sum(v[0] for v in rows.values()); n = sum(v[1] for v in rows.values())
    lines.append(f"{'raw, all strata':<18} {k:>3}/{n:<4} {k / n:6.1%}  (sample mix, not traffic)")
    lines.append(f"{'traffic-weighted':<18}          {weighted_rate(rows, shares):6.1%}")
    return "\n".join(lines)


def rare_failure_line(name, failures, n, target):
    ub = upper_bound(failures, n)
    need = traces_needed(target, failures)
    return (f"{name}: {failures} in {n}; one-sided 95% upper bound {ub:.1%}; "
            f"target under {target:.1%} needs {need} traces at this failure count")
