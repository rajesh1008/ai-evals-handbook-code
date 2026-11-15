"""Truss 0.20 (Chapter 17): bias. A battery of perturbation tests for a model judge.

The module never calls a model. It scores pairwise and pointwise verdicts under
controlled perturbations (position swap, length padding, authorship labels,
authority cues, rubric option order, segment slices), reports flip rates with
Wilson intervals, measures a panel's shared mistakes, and says whether a bias
disqualifies the judge from a role.
"""
from collections import Counter, defaultdict

from .fields import wilson

try:
    from .judge import pair_outcome
except ImportError:  # Chapter 16's module may still be in flight
    def pair_outcome(first_order, swapped_order):
        m1 = {"A": "original", "B": "other", "tie": "tie"}.get(first_order, "unparsed")
        m2 = {"B": "original", "A": "other", "tie": "tie"}.get(swapped_order, "unparsed")
        if "unparsed" in (m1, m2):
            return "unparsed"
        return m1 if m1 == m2 else "position"


# Harbor's default thresholds, signed in Chapter 17. A value at or above `flag`
# is reported; at or above `fail` it can disqualify the role that depends on it.
THRESHOLDS = {
    "position_rate":   {"flag": 0.05, "fail": 0.10},
    "verbosity_flip":  {"flag": 0.05, "fail": 0.15},
    "self_pref":       {"flag": 0.05, "fail": 0.15},
    "label_shift":     {"flag": 0.05, "fail": 0.15},
    "authority_flip":  {"flag": 0.02, "fail": 0.08},
    "rubric_slot":     {"flag": 0.10, "fail": 0.25},
    "segment_gap":     {"flag": 0.10, "fail": 0.20},
}


def grade(value, flag, fail):
    """'pass', 'flag' or 'fail' for a rate read against a pair of cut-offs."""
    if value != value:  # NaN
        return "unparsed"
    if value >= fail:
        return "fail"
    if value >= flag:
        return "flag"
    return "pass"


def _rate(k, n):
    return k / n if n else float("nan")


def _ci(k, n):
    return wilson(k, n) if n else (float("nan"), float("nan"))


# ------------------------------------------------------------------ position

def position_calls(first_orders, swapped_orders):
    """One pair_outcome per pair: original, other, tie, position or unparsed."""
    return [pair_outcome(a, b) for a, b in zip(first_orders, swapped_orders)]


def position_summary(calls):
    """Consistency under a swap of the two slots.

    `position_rate` is the share of pairs where the judge picked the same slot
    both times (the choice followed the slot, not the reply). Consistency is
    the complementary share among parsed calls. Dual-order mitigation keeps
    only the consistent calls.
    """
    c = Counter(calls)
    n = len(calls)
    parsed = n - c["unparsed"]
    pos = c["position"]
    consistent = c["original"] + c["other"] + c["tie"]
    return {
        "n": n, "parsed": parsed,
        "original": c["original"], "other": c["other"], "tie": c["tie"],
        "position": pos, "unparsed": c["unparsed"],
        "position_rate": _rate(pos, parsed), "position_ci": _ci(pos, parsed),
        "consistency": _rate(consistent, parsed),
        "kept_after_mitigation": consistent,
    }


def mitigate_position(first_orders, swapped_orders, gold=None):
    """Drop pairs whose two orders disagree on the winner (position outcomes).

    Returns the consistent picks mapped back to the original reply ('A' means
    the originally-first reply won) and, if gold is given, accuracy on the kept
    pairs only.
    """
    kept, kept_gold = [], []
    for i, (a, b) in enumerate(zip(first_orders, swapped_orders)):
        o = pair_outcome(a, b)
        if o in ("original", "other", "tie"):
            pick = {"original": "A", "other": "B", "tie": "tie"}[o]
            kept.append(pick)
            if gold is not None:
                kept_gold.append(gold[i])
    out = {"kept": kept, "n": len(kept)}
    if gold is not None:
        right = sum(p == g for p, g in zip(kept, kept_gold) if g != "tie")
        denom = sum(g != "tie" for g in kept_gold)
        out["accuracy"] = _rate(right, denom)
        out["n_scored"] = denom
    return out


# ------------------------------------------------------------------ verbosity and cues

def flip_summary(base, perturbed, toward=None):
    """Share of items whose pick changed when a single feature was perturbed.

    If `toward` is a list (one label per item, e.g. 'A' when A was padded),
    `toward_rate` is the share of flips that moved onto that label.
    """
    n = len(base)
    flips = [i for i in range(n) if base[i] != perturbed[i]]
    toward_n = 0
    if toward is not None:
        toward_n = sum(1 for i in flips if perturbed[i] == toward[i])
    return {
        "n": n, "flipped": len(flips), "flip_rate": _rate(len(flips), n),
        "flip_ci": _ci(len(flips), n), "where": flips,
        "toward": toward_n, "toward_rate": _rate(toward_n, len(flips)),
    }


# ------------------------------------------------------------------ self-preference

def self_pref_summary(rows):
    """Gold-controlled self-preference on pairwise picks.

    Each row: judge_family, gen_A, gen_B, pick ('A'/'B'/'tie'), gold ('A'/'B'/'tie'),
    and optionally quality_matched (bool). Among quality-matched pairs (or all
    pairs whose gold is 'tie'), the score is P(pick own family) - P(pick the
    other family). Pairs where both sides share the judge's family, or neither
    does, are skipped.
    """
    own = other = skip = 0
    used = 0
    for r in rows:
        matched = r.get("quality_matched")
        if matched is False:
            continue
        if matched is None and r.get("gold") not in ("tie", None):
            # default: only tied-quality pairs, unless the caller marks them
            continue
        a_own = r["gen_A"] == r["judge_family"]
        b_own = r["gen_B"] == r["judge_family"]
        if a_own == b_own:
            skip += 1
            continue
        used += 1
        pick = r["pick"]
        if pick == "tie":
            continue
        if (pick == "A" and a_own) or (pick == "B" and b_own):
            own += 1
        else:
            other += 1
    decisive = own + other
    pref = _rate(own, decisive) - _rate(other, decisive) if decisive else float("nan")
    return {
        "used": used, "skipped_same_or_neither": skip, "own": own, "other": other,
        "decisive": decisive, "self_pref": pref,
        "own_rate": _rate(own, decisive), "own_ci": _ci(own, decisive),
    }


def label_shift_summary(blind_picks, labeled_picks, labeled_side):
    """Authorship-label test: same replies, a 'self' or 'other' tag added.

    `labeled_side` is 'A' or 'B' (which reply received the tag) or a list.
    Returns the flip rate and the share of flips that moved onto a 'self' tag
    or away from an 'other' tag.
    """
    if isinstance(labeled_side, str):
        labeled_side = [labeled_side] * len(blind_picks)
    toward = []
    for i, side in enumerate(labeled_side):
        tag = labeled_picks[i]  # we need the tag type too; encode as 'self:A'
        toward.append(side)
    # The caller passes labeled picks and a parallel list of tag kinds.
    return flip_summary(blind_picks, labeled_picks, toward=toward)


def label_effect(blind, tagged, tags):
    """tags[i] is ('self'|'other', 'A'|'B'). Measures directional label pull."""
    n = len(blind)
    toward_self = away_other = flips = 0
    for i in range(n):
        if blind[i] == tagged[i]:
            continue
        flips += 1
        kind, side = tags[i]
        if kind == "self" and tagged[i] == side:
            toward_self += 1
        if kind == "other" and blind[i] == side and tagged[i] != side:
            away_other += 1
    directional = toward_self + away_other
    return {
        "n": n, "flipped": flips, "flip_rate": _rate(flips, n),
        "flip_ci": _ci(flips, n),
        "toward_self": toward_self, "away_other": away_other,
        "directional": directional,
        "label_shift": _rate(directional, n),
    }


# ------------------------------------------------------------------ rubric anchoring

def rubric_anchor(picks_by_order, n_options=None):
    """Position bias over rubric options (the multiple-choice form).

    `picks_by_order` is a list of (order, picked_option) where `order` is a
    sequence of option names (e.g. ('pass', 'fail', 'cannot_tell')) and
    `picked_option` is one of them. Excess first-slot rate is
    P(first slot) - 1/n_options.
    """
    first = last = content = total = 0
    by_option = Counter()
    by_slot = Counter()
    # Group by an item index if the caller packed one; otherwise treat each
    # record independently for slot preference, and measure content
    # consistency when the same item appears under two or more orders.
    items = defaultdict(list)
    for rec in picks_by_order:
        if len(rec) == 3:
            item, order, pick = rec
        else:
            order, pick = rec
            item = None
        order = tuple(order)
        n_opt = n_options or len(order)
        total += 1
        by_option[pick] += 1
        if pick in order:
            slot = order.index(pick)
            by_slot[slot] += 1
            if slot == 0:
                first += 1
            if slot == n_opt - 1:
                last += 1
        if item is not None:
            items[item].append(pick)
    n_opt = n_options or (max(len(r[-2]) if len(r) == 3 else len(r[0])
                              for r in picks_by_order) if picks_by_order else 0)
    consistent_items = sum(1 for vs in items.values() if len(set(vs)) == 1)
    return {
        "n": total, "n_options": n_opt,
        "first": first, "last": last,
        "first_rate": _rate(first, total), "first_ci": _ci(first, total),
        "last_rate": _rate(last, total),
        "excess_first": _rate(first, total) - (1 / n_opt if n_opt else float("nan")),
        "by_option": dict(by_option), "by_slot": dict(by_slot),
        "items": len(items),
        "content_consistent": consistent_items,
        "content_consistency": _rate(consistent_items, len(items)),
    }


# ------------------------------------------------------------------ segments

def segment_table(rows, value="position_rate"):
    """Per-segment rates and the largest gap between any two segments.

    Each row: {segment, success} (bool or 0/1), or {segment, k, n}. The
    largest absolute gap in the success rate is `max_gap`.
    """
    buckets = defaultdict(lambda: [0, 0])
    for r in rows:
        s = r["segment"]
        if "k" in r and "n" in r:
            buckets[s][0] += r["k"]
            buckets[s][1] += r["n"]
        else:
            buckets[s][0] += int(bool(r.get("success")))
            buckets[s][1] += 1
    table = {}
    rates = []
    for s, (k, n) in sorted(buckets.items()):
        table[s] = {"k": k, "n": n, "rate": _rate(k, n), "ci": _ci(k, n)}
        if n:
            rates.append(table[s]["rate"])
    table["_max_gap"] = (max(rates) - min(rates)) if len(rates) >= 2 else 0.0
    return table


# ------------------------------------------------------------------ panel

def majority(picks, tie="tie"):
    """Element-wise majority across judges. Ties (no strict majority) become `tie`."""
    out = []
    n_j = len(picks)
    if not n_j:
        return out
    for vs in zip(*picks):
        (top, k), *_ = Counter(vs).most_common() + [(None, 0)]
        out.append(top if k > n_j / 2 else tie)
    return out


def pairwise_agree(a, b):
    n = len(a)
    k = sum(x == y for x, y in zip(a, b))
    return {"n": n, "agree": k, "rate": _rate(k, n), "ci": _ci(k, n)}


def correlated_errors(a, b, gold):
    """Shared mistakes against gold, compared with independence.

    `both_given_either` is P(both wrong | at least one wrong). Independence
    would give (pa*pb) / (pa + pb - pa*pb) where pa, pb are each judge's
    error rates. A ratio above 1 means the judges share blind spots.
    """
    n = sum(g != "tie" for g in gold)
    both = one = a_wrong = b_wrong = 0
    for x, y, g in zip(a, b, gold):
        if g == "tie":
            continue
        wa, wb = (x != g), (y != g)
        a_wrong += wa
        b_wrong += wb
        both += wa and wb
        one += wa or wb
    pa, pb = _rate(a_wrong, n), _rate(b_wrong, n)
    indep_both = pa * pb
    indep_either = pa + pb - indep_both
    obs = _rate(both, n)
    return {
        "n": n, "a_wrong": a_wrong, "b_wrong": b_wrong, "both": both, "either": one,
        "a_rate": pa, "b_rate": pb,
        "both_rate": obs, "both_ci": _ci(both, n),
        "both_given_either": _rate(both, one),
        "indep_both": indep_both,
        "ratio": (obs / indep_both) if indep_both else float("nan"),
        "indep_either": indep_either,
    }


# ------------------------------------------------------------------ battery and admission

def evaluate_tests(metrics, thresholds=None):
    """metrics: {name: value} using the keys of THRESHOLDS (or a subset)."""
    th = thresholds or THRESHOLDS
    rows = []
    for name, value in metrics.items():
        cuts = th[name]
        rows.append({
            "name": name, "value": value,
            "flag": cuts["flag"], "fail": cuts["fail"],
            "verdict": grade(value, cuts["flag"], cuts["fail"]),
        })
    return rows


def disqualify(rows, role="order"):
    """Whether the battery keeps the judge in `role`.

    Rules Harbor signed in Chapter 17:
    - a flag never disqualifies on its own;
    - a fail on a test the role depends on disqualifies that role
      (order / pairwise depends on position_rate; pointwise depends on
      rubric_slot; every role depends on authority_flip and segment_gap);
    - two or more fails, on any tests, disqualify every role;
    - role 'decide' is refused here (Chapter 18's Judge Report Card is required).
    """
    fails = [r for r in rows if r["verdict"] == "fail"]
    flags = [r for r in rows if r["verdict"] == "flag"]
    names = {r["name"] for r in fails}
    reasons = []
    if role == "decide":
        reasons.append("role decide needs a Judge Report Card")
    depends = {
        "order": {"position_rate", "authority_flip", "segment_gap", "self_pref"},
        "pairwise": {"position_rate", "verbosity_flip", "self_pref"},
        "pointwise": {"rubric_slot", "authority_flip", "segment_gap"},
        "none": set(),
    }.get(role, {"position_rate"})
    critical = sorted(names & depends)
    if critical:
        reasons.append("fail on " + ", ".join(critical))
    if len(fails) >= 2:
        reasons.append(f"{len(fails)} tests at fail")
    return {
        "admit": not reasons, "role": role if not reasons else "none",
        "fails": [r["name"] for r in fails],
        "flags": [r["name"] for r in flags],
        "reasons": reasons,
    }
