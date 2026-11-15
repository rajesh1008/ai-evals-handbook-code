"""Chapter 15: the metric suite for one flow, assembled.

A decision table that drops any metric no decision depends on; a composition audit that compares a gate
set with the traffic it stands for, segment by segment, and refuses a set whose segments are thin or
missing; a two-direction gate on a stochastic system (a case is newly failing only when the candidate
fails it on every rerun and production passed it on every rerun); the reachability check that says
whether any sample size could show a rate under its target; and the sample size and weeks to get there.
"""
from collections import Counter
from dataclasses import dataclass
from math import ceil

from .rates import upper_bound, wilson, traces_needed


@dataclass
class Row:
    metric: str                  # card id or signal name
    question: str                # the binary question the metric answers
    threshold: str = ""          # what value triggers the action
    owner: str = ""              # the person who acts
    action: str = ""             # what that person does when the threshold is crossed
    tier: str = "monitor"        # gate, monitor, inform


def decision_table(rows):
    """Keep a gate or monitor row only when it names a threshold, an owner and an action. A metric that
    changes no decision is dropped with the reason, so the table says why it is not there. An inform
    signal decides nothing by definition (Chapter 8), so it needs only an owner."""
    kept, dropped = [], []
    for r in rows:
        need = ("owner",) if r.tier == "inform" else ("threshold", "owner", "action")
        missing = [k for k in need if not getattr(r, k).strip()]
        if missing:
            dropped.append((r, "no " + ", no ".join(missing)))
        else:
            kept.append(r)
    gates = [r for r in kept if r.tier == "gate"]
    return {"kept": kept, "dropped": dropped, "gates": gates}


def composition_audit(gate, frame, key, *, min_n=20, min_ratio=0.5):
    """Compare segment shares in a gate set against the traffic frame.

    gate, frame: lists of cases; key(case) -> segment name (or a list of names, for overlapping flags).
    A segment fails when the gate holds fewer than min_n cases of it or its share is under min_ratio times
    its share of traffic. Segments in the frame but absent from the gate always fail.
    """
    def counts(cases):
        c = Counter()
        for x in cases:
            k = key(x)
            for s in (k if isinstance(k, (list, tuple, set)) else [k]):
                c[s] += 1
        return c
    g, f = counts(gate), counts(frame)
    rows = {}
    for s in sorted(set(f) | set(g)):
        gs, fs = g[s] / len(gate) if gate else 0.0, f[s] / len(frame) if frame else 0.0
        ratio = gs / fs if fs else None
        why = []
        if f[s] and g[s] < min_n:
            why.append(f"{g[s]} cases, minimum {min_n}")
        if fs and gs < min_ratio * fs:
            why.append(f"share {gs:.1%} against {fs:.1%} of traffic")
        rows[s] = {"gate_n": g[s], "gate_share": gs, "frame_n": f[s], "frame_share": fs, "ratio": ratio,
                   "pass": not why, "why": "; ".join(why)}
    failing = [s for s, r in rows.items() if not r["pass"]]
    return {"segments": rows, "verdict": "refuse" if failing else "accept", "failing": failing}


def newly_failing(base_runs, cand_runs):
    """base_runs, cand_runs: lists of {case: failed?} (one dict per rerun, same cases).
    Stable new failures: the candidate failed on every rerun and production passed on every rerun.
    Also returns the cases that flipped within production's own reruns (the noise floor)."""
    cases = base_runs[0].keys()
    new = sorted(c for c in cases if all(r[c] for r in cand_runs) and not any(r[c] for r in base_runs))
    unstable = sorted(c for c in cases if len({r[c] for r in base_runs}) > 1)
    single = sorted(c for c in cases if any(r[c] for r in cand_runs) and not any(r[c] for r in base_runs))
    return {"new": new, "single_run": sorted(set(single) - set(new)), "production_flips": unstable}


def two_way_gate(required, base_runs, cand_runs, offer="draft_deferral"):
    """Gate a decision step in both directions on the same cases.

    required: {case: required action}; base_runs, cand_runs: lists of {case: action} (reruns).
    Wrong offer: the offer action where policy requires something else. Wrongful refusal: anything else
    where policy requires the offer. The candidate holds if either direction has a stable new failure."""
    def fails(runs, kind):
        out = []
        for r in runs:
            if kind == "offer":
                out.append({c: r[c] == offer and required[c] != offer for c in required})
            else:
                out.append({c: r[c] != offer and required[c] == offer for c in required})
        return out
    res = {}
    for kind in ("offer", "refusal"):
        b, c = fails(base_runs, kind), fails(cand_runs, kind)
        n = len(required) if kind == "offer" else sum(v == offer for v in required.values())
        res[kind] = {**newly_failing(b, c), "n": n, "base": [sum(x.values()) for x in b], "cand": [sum(x.values()) for x in c]}
    acc = lambda runs: [sum(r[c] == required[c] for c in required) for r in runs]
    res["accuracy"] = {"base": acc(base_runs), "cand": acc(cand_runs), "n": len(required)}
    holds = [k for k in ("offer", "refusal") if res[k]["new"]]
    res["verdict"] = "hold" if holds else "ship"
    res["holds_on"] = holds
    return res


def reachable(failures, n, target, confidence=0.95):
    """Can more sampling alone show the rate under target? Not when the observed rate is at or above it:
    if the true rate is what we observed, the bound converges on that rate, never under the target."""
    p = failures / n
    lo, hi = wilson(failures, n)
    ub = upper_bound(failures, n, confidence)
    return {"rate": p, "wilson": (lo, hi), "upper": ub, "target": target,
            "reachable_by_sampling": p < target, "shown": ub < target}


def needed_at(rate, target, confidence=0.95, cap=200000):
    """Smallest n at which the bound falls under target when failures arrive at the given true rate
    (failures = round(rate * n)). None when the rate is at or above the target."""
    if rate >= target:
        return None
    n = 1
    while n <= cap:
        if upper_bound(round(rate * n), n, confidence) < target:
            return n
        n = max(n + 1, ceil(n * 1.01))
    return None


def refine(rate, target, confidence=0.95):
    """needed_at, then walked back one at a time to the smallest n."""
    n = needed_at(rate, target, confidence)
    if n is None:
        return None
    while n > 1 and upper_bound(round(rate * (n - 1)), n - 1, confidence) < target:
        n -= 1
    return n


def weeks_to(n_needed, have, per_week):
    if n_needed is None:
        return None
    return max(0.0, (n_needed - have) / per_week)


__all__ = ["Row", "decision_table", "composition_audit", "newly_failing", "two_way_gate", "reachable",
           "needed_at", "refine", "weeks_to", "traces_needed"]
