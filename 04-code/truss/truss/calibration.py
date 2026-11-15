"""Truss 0.23 (Chapter 20): calibration. Calibration report and routing simulator.

The book calls this release Truss v3.5. The module never calls a model. It
scores confidence values that a system already wrote onto its traces against
gold correctness, and turns a calibrated score into a route.

- reliability_table, ece, mce, brier, brier_decomposition, auroc: what a
  confidence number means (calibration) and whether it can rank (separation).
- degenerate: refuses a confidence field that is missing, out of range or
  (near) constant, the field that passes every schema check and means nothing.
- fit_isotonic / apply_map / CalibrationMap: a monotone recalibration map,
  content-addressed with the model pin and policy digest it was fitted under,
  so a model or policy change voids it.
- crc_threshold, cp_threshold, feasibility_floor: thresholds for the auto
  route from a labelled set, with a finite-sample guarantee.
- route, simulate_routing, post_review_estimate: three routes (auto, review,
  refuse), fail-closed rules, officer load and post-review error.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter

from .rates import upper_bound, wilson

ROUTES = ("auto", "review", "refuse")


# ---------------------------------------------------------------- calibration

def _check(conf, correct):
    conf = [float(c) for c in conf]
    correct = [bool(x) for x in correct]
    if len(conf) != len(correct):
        raise ValueError("conf and correct must be the same length")
    if not conf:
        raise ValueError("empty input")
    return conf, correct


def _edges(conf, bins, strategy):
    if strategy == "uniform":
        return [i / bins for i in range(bins + 1)]
    if strategy == "quantile":
        s = sorted(conf)
        n = len(s)
        e = [0.0] + [s[min(n - 1, int(math.ceil(n * i / bins)) - 1)] for i in range(1, bins)] + [1.0]
        out = [e[0]]
        for x in e[1:]:
            if x > out[-1]:
                out.append(x)
        if out[-1] < 1.0:
            out.append(1.0)
        return out
    raise ValueError("strategy must be 'uniform' or 'quantile'")


def reliability_table(conf, correct, bins=10, strategy="uniform"):
    """Rows of (lo, hi, n, mean confidence, accuracy, gap) per bin; empty bins skipped.

    Bins are closed on the right: (lo, hi]; the first bin also takes 0.
    """
    conf, correct = _check(conf, correct)
    e = _edges(conf, bins, strategy)
    rows = []
    for i in range(len(e) - 1):
        lo, hi = e[i], e[i + 1]
        idx = [j for j, c in enumerate(conf) if (lo < c <= hi) or (i == 0 and c == lo)]
        if not idx:
            continue
        mc = sum(conf[j] for j in idx) / len(idx)
        acc = sum(correct[j] for j in idx) / len(idx)
        rows.append({"lo": lo, "hi": hi, "n": len(idx), "conf": mc, "acc": acc,
                     "gap": mc - acc})
    return rows


def ece(conf, correct, bins=10, strategy="uniform"):
    """Expected calibration error: bin-weighted mean |confidence - accuracy|."""
    rows = reliability_table(conf, correct, bins, strategy)
    n = sum(r["n"] for r in rows)
    return sum(r["n"] / n * abs(r["gap"]) for r in rows)


def mce(conf, correct, bins=10, strategy="uniform", min_n=1):
    """Maximum calibration error over bins holding at least min_n cases."""
    rows = [r for r in reliability_table(conf, correct, bins, strategy) if r["n"] >= min_n]
    return max(abs(r["gap"]) for r in rows)


def brier(conf, correct):
    conf, correct = _check(conf, correct)
    return sum((c - y) ** 2 for c, y in zip(conf, correct)) / len(conf)


def brier_decomposition(conf, correct, bins=10, strategy="uniform"):
    """Murphy decomposition on binned forecasts: reliability - resolution + uncertainty.

    Reliability is the calibration penalty, resolution the credit for sorting
    cases into groups whose accuracy differs from the base rate. A constant
    confidence has zero resolution whatever its value.
    """
    conf, correct = _check(conf, correct)
    rows = reliability_table(conf, correct, bins, strategy)
    n = len(conf)
    base = sum(correct) / n
    rel = sum(r["n"] * (r["conf"] - r["acc"]) ** 2 for r in rows) / n
    res = sum(r["n"] * (r["acc"] - base) ** 2 for r in rows) / n
    unc = base * (1 - base)
    return {"reliability": rel, "resolution": res, "uncertainty": unc,
            "brier_binned": rel - res + unc, "base_rate": base}


def auroc(conf, correct):
    """Probability that a right case outscores a wrong one (ties count half).

    This is separation, the property routing needs; 0.5 is no better than a coin.
    """
    conf, correct = _check(conf, correct)
    pos = [c for c, y in zip(conf, correct) if y]
    neg = [c for c, y in zip(conf, correct) if not y]
    if not pos or not neg:
        return float("nan")
    order = sorted(set(conf))
    rank = {}
    allv = sorted(conf)
    # average ranks for ties
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        rank[allv[i]] = (i + j) / 2 + 1
        i = j + 1
    r_pos = sum(rank[c] for c in pos)
    n1, n0 = len(pos), len(neg)
    return (r_pos - n1 * (n1 + 1) / 2) / (n1 * n0)


def degenerate(conf, mode_share_max=0.5, min_distinct=5):
    """Reasons a confidence field cannot be used for routing (empty list = usable).

    A field filled with one default value passes a schema that asks for a float
    between 0 and 1. This check asks whether the field could carry information.
    """
    vals = list(conf)
    reasons = []
    n = len(vals)
    missing = sum(v is None or (isinstance(v, float) and v != v) for v in vals)
    present = [float(v) for v in vals if not (v is None or (isinstance(v, float) and v != v))]
    if missing:
        reasons.append(f"missing:{missing}/{n}")
    if any(v < 0 or v > 1 for v in present):
        reasons.append("out_of_range")
    if present:
        mode, cnt = Counter(present).most_common(1)[0]
        if cnt / len(present) > mode_share_max:
            reasons.append(f"mode_share:{cnt}/{len(present)}@{mode:g}")
        if len(set(present)) < min_distinct:
            reasons.append(f"distinct:{len(set(present))}")
    return reasons


# ---------------------------------------------------------------- recalibration

def fit_isotonic(conf, correct):
    """Pool-adjacent-violators fit of P(correct | conf). Returns sorted knots [(x, p)]."""
    conf, correct = _check(conf, correct)
    pts = sorted(zip(conf, correct))
    blocks = []  # [sum_y, n, x_max]
    for x, y in pts:
        blocks.append([float(y), 1, x])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] >= blocks[-1][0] / blocks[-1][1]:
            s, n, xm = blocks.pop()
            blocks[-1][0] += s
            blocks[-1][1] += n
            blocks[-1][2] = xm
    return [(b[2], b[0] / b[1]) for b in blocks]


def _logit(p, eps=1e-6):
    p = min(1 - eps, max(eps, float(p)))
    return math.log(p / (1 - p))


def _sig(t):
    if t >= 0:
        return 1 / (1 + math.exp(-t))
    e = math.exp(t)
    return e / (1 + e)


def _nll(a, b, xs, ys):
    tot = 0.0
    for x, y in zip(xs, ys):
        p = min(1 - 1e-12, max(1e-12, _sig(a * x + b)))
        tot -= y * math.log(p) + (1 - y) * math.log(1 - p)
    return tot


def fit_platt(conf, correct, iters=100):
    """Logistic recalibration on the logit of the raw score: P = sigmoid(a * logit(c) + b).

    Two parameters, monotone and smooth, so it is stable on a few hundred labels
    where an isotonic map would be a staircase with a handful of steps. Damped
    Newton steps with step halving on the negative log-likelihood. Targets use
    Platt's smoothing, (N+ + 1) / (N+ + 2) and 1 / (N- + 2), so a set with no
    overlap between right and wrong cases still gives a finite map.
    """
    conf, correct = _check(conf, correct)
    xs = [_logit(c) for c in conf]
    npos = sum(correct); nneg = len(correct) - npos
    hi, lo = (npos + 1) / (npos + 2), 1 / (nneg + 2)
    ys = [hi if y else lo for y in correct]
    a, b = 1.0, 0.0
    cur = _nll(a, b, xs, ys)
    for _ in range(iters):
        ga = gb = haa = hab = hbb = 0.0
        for x, y in zip(xs, ys):
            p = _sig(a * x + b)
            w = p * (1 - p)
            ga += (y - p) * x
            gb += (y - p)
            haa += w * x * x
            hab += w * x
            hbb += w
        haa += 1e-6; hbb += 1e-6
        det = haa * hbb - hab * hab
        da = (hbb * ga - hab * gb) / det
        db = (haa * gb - hab * ga) / det
        step = 1.0
        while step > 1e-6:
            na, nb = a + step * da, b + step * db
            new = _nll(na, nb, xs, ys)
            if new <= cur:
                break
            step /= 2
        if step <= 1e-6 or cur - new < 1e-12:
            a, b = (na, nb) if new <= cur else (a, b)
            break
        a, b, cur = na, nb, new
    return a, b


def apply_platt(a, b, x):
    return _sig(a * _logit(x) + b)


def apply_knots(knots, x):
    """Step function: the value of the first knot whose x_max is at or above x."""
    for xm, p in knots:
        if x <= xm:
            return p
    return knots[-1][1]


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]


def calibration_map(conf, correct, model_pin, policy_digest, fit_set_digest, source, kind="platt"):
    """A recalibration map bound to the model pin and policy it was fitted under."""
    rec = {"source": source, "model_pin": model_pin, "policy_digest": policy_digest,
           "fit_set_digest": fit_set_digest, "n": len(conf), "kind": kind}
    if kind == "platt":
        a, b = fit_platt(conf, correct)
        rec["params"] = [round(a, 6), round(b, 6)]
    elif kind == "isotonic":
        rec["knots"] = [[round(x, 6), round(p, 6)] for x, p in fit_isotonic(conf, correct)]
    else:
        raise ValueError("kind must be 'platt' or 'isotonic'")
    rec["digest"] = _digest(rec)
    return rec


def map_valid_for(cmap, model_pin, policy_digest):
    """Reasons the map may not be used for this build (empty list = valid)."""
    reasons = []
    if cmap is None:
        return ["no_map"]
    if cmap["model_pin"] != model_pin:
        reasons.append("model_pin_changed")
    if cmap["policy_digest"] != policy_digest:
        reasons.append("policy_changed")
    return reasons


def apply_map(cmap, x):
    if cmap.get("kind", "isotonic") == "platt":
        a, b = cmap["params"]
        return apply_platt(a, b, x)
    return apply_knots([tuple(k) for k in cmap["knots"]], x)


# ---------------------------------------------------------------- thresholds

def feasibility_floor(base_error, alpha, max_loss=1.0):
    """Least share of cases that must leave the auto route when base error exceeds alpha.

    For a loss bounded by max_loss, any method whose auto route keeps expected
    error at or under alpha must withhold at least (mu - alpha) / (M - alpha).
    """
    if base_error <= alpha:
        return 0.0
    return (base_error - alpha) / (max_loss - alpha)


def _auto_stats(scores, errors, t):
    idx = [i for i, s in enumerate(scores) if s >= t]
    k = sum(errors[i] for i in idx)
    return len(idx), k


def crc_threshold(scores, errors, alpha, candidates=None):
    """Lowest threshold whose conformal risk bound on the auto route is at most alpha.

    Binary loss, bounded by 1: (k + 1) / (n_auto + 1) <= alpha, where k errors
    fall among n_auto calibration cases at or above t. The guarantee is on the
    expected error of the auto route for an exchangeable new case, not a bound
    for any one week.
    """
    errors = [bool(e) for e in errors]
    cands = sorted(set(candidates if candidates is not None else scores))
    for t in cands:
        n, k = _auto_stats(scores, errors, t)
        if n and (k + 1) / (n + 1) <= alpha:
            return {"t": t, "n_auto": n, "errors": k, "bound": (k + 1) / (n + 1),
                    "share": n / len(scores)}
    return None


def cp_threshold(scores, errors, alpha, confidence=0.95, candidates=None):
    """Lowest threshold whose exact one-sided upper bound on auto error is at most alpha."""
    errors = [bool(e) for e in errors]
    cands = sorted(set(candidates if candidates is not None else scores))
    for t in cands:
        n, k = _auto_stats(scores, errors, t)
        if n and upper_bound(k, n, confidence) <= alpha:
            return {"t": t, "n_auto": n, "errors": k, "bound": upper_bound(k, n, confidence),
                    "share": n / len(scores)}
    return None


# ---------------------------------------------------------------- routing

def route(score, flags=(), t_auto=0.97, t_refuse=0.60, map_reasons=(), field_reasons=()):
    """One case to auto, review or refuse, with the reason. Fails closed.

    - map or field unusable (model or policy changed, constant or missing
      confidence): review. The system keeps drafting; a person sees everything.
    - score missing on this case: refuse (no draft is shown to the officer).
    - any forced-review flag (a failed code check, a segment with a known blind
      spot): review.
    - score below t_refuse: refuse. At or above t_auto: auto. Otherwise review.
    """
    if map_reasons or field_reasons:
        return "review", "fail_closed:" + ",".join(list(map_reasons) + list(field_reasons))
    if score is None or (isinstance(score, float) and score != score):
        return "refuse", "fail_closed:missing_score"
    if flags:
        return "review", "flag:" + ",".join(flags)
    if score < t_refuse:
        return "refuse", "below_refuse"
    if score >= t_auto:
        return "auto", "above_auto"
    return "review", "between"


def simulate_routing(cases, t_auto, t_refuse, outcome, minutes=None, capacity_minutes=None,
                     map_reasons=(), field_reasons=(), policy=None):
    """Route every case and score what reaches the borrower.

    cases: dicts with 'score', 'flags', 'correct' and any keys outcome() needs.
    outcome(case, route, overloaded) -> True if the final outcome is wrong.
    minutes: officer minutes per route (auto, review, refuse).
    capacity_minutes: officer minutes available for the same cases; when the
    load exceeds it, outcome() is told the officers are overloaded.
    policy: optional function case -> (route, reason) replacing route(), for
    comparing a rule that does not use confidence (for example, by kind).
    """
    minutes = minutes or {"auto": 0.0, "review": 4.0, "refuse": 12.0}
    counts = Counter()
    reasons = Counter()
    routed = []
    for c in cases:
        if policy is not None:
            r, why = policy(c)
        else:
            r, why = route(c.get("score"), c.get("flags", ()), t_auto, t_refuse, map_reasons, field_reasons)
        counts[r] += 1
        reasons[why.split(":")[0]] += 1
        routed.append((c, r))
    n = len(cases)
    load = sum(counts[r] * minutes[r] for r in ROUTES)
    overloaded = capacity_minutes is not None and load > capacity_minutes
    wrong = Counter()
    for c, r in routed:
        if outcome(c, r, overloaded):
            wrong[r] += 1
    res = {
        "n": n,
        "share": {r: counts[r] / n for r in ROUTES},
        "count": {r: counts[r] for r in ROUTES},
        "wrong": {r: wrong[r] for r in ROUTES},
        "route_error": {r: (wrong[r] / counts[r] if counts[r] else float("nan")) for r in ROUTES},
        "post_review_error": sum(wrong.values()) / n,
        "post_review_wrong": sum(wrong.values()),
        "officer_minutes": load,
        "reasons": dict(reasons),
        "overloaded": overloaded,
    }
    if capacity_minutes is not None:
        res["capacity_minutes"] = capacity_minutes
    return res


def post_review_estimate(strata, z=1.96):
    """Stratified estimate of post-review error from labelled draws per route.

    strata: {route: (share_of_traffic, wrong_in_sample, sample_n)}. Returns the
    weighted rate and a normal-approximation interval built from per-stratum
    Wilson-centred variances (adequate for a weekly report; the exact pooled
    bound is in the scoreboard text).
    """
    est = 0.0
    var = 0.0
    for r, (w, k, n) in strata.items():
        if n == 0:
            continue
        lo, hi = wilson(k, n)
        p = k / n
        p_adj = (k + 2) / (n + 4)  # Agresti-Coull centre keeps zero-cell strata honest
        est += w * p
        var += w * w * p_adj * (1 - p_adj) / n
    se = math.sqrt(var)
    return {"rate": est, "lo": max(0.0, est - z * se), "hi": est + z * se, "se": se}
