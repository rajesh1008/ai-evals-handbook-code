"""Truss 0.24 (Chapter 21): trial. What to do with a judge that fails validation.

The module never calls a model. It lays out a judge's validation table by kind and segment, sorts
the disagreements by cause and says which causes are arithmetic that code already does, measures
the construct-validity profile of a judge (invariance under edits that should not move a verdict,
sensitivity under minimal edits that should), checks how much of a verdict a single surface feature
reproduces, bounds the share of offers a judge would let through against a target, admits the
parts of a split judge one by one, and writes the decision record for fix, split or abandon.
"""
from collections import Counter, defaultdict

from .adjudication import kappa
from .fields import wilson
from .rates import upper_bound, traces_needed

POSITIVE = "fail"


def validation_table(truth, pred, kinds, segments=None, positive=POSITIVE):
    """The trial table: overall confusion (abstentions counted as misses, as in Chapter 16), TPR and
    TNR with Wilson intervals, raw agreement, kappa, and one row per gold kind and per segment."""
    out = {"n": len(truth)}
    c = Counter()
    for t, p in zip(truth, pred):
        if p not in ("pass", "fail"):
            c["abstain_pos" if t == positive else "abstain_neg"] += 1
        elif t == positive:
            c["tp" if p == positive else "fn"] += 1
        else:
            c["fp" if p == positive else "tn"] += 1
    P = c["tp"] + c["fn"] + c["abstain_pos"]
    N = c["tn"] + c["fp"] + c["abstain_neg"]
    out.update({k: c[k] for k in ("tp", "fn", "fp", "tn", "abstain_pos", "abstain_neg")})
    out.update({"P": P, "N": N,
                "tpr": c["tp"] / P if P else float("nan"), "tpr_ci": wilson(c["tp"], P),
                "tnr": c["tn"] / N if N else float("nan"), "tnr_ci": wilson(c["tn"], N),
                "agree_n": sum(1 for t, p in zip(truth, pred) if t == p),
                "kappa": kappa(list(truth), list(pred))})
    out["agreement"] = out["agree_n"] / len(truth) if truth else float("nan")
    rows = defaultdict(Counter)
    for k, t, p in zip(kinds, truth, pred):
        rows[k]["n"] += 1
        rows[k]["gold_fail"] += t == positive
        rows[k]["right"] += t == p
        rows[k]["abstain"] += p not in ("pass", "fail")
    out["by_kind"] = {k: dict(v) for k, v in sorted(rows.items())}
    if segments is not None:
        seg = defaultdict(lambda: ([], []))
        for s, t, p in zip(segments, truth, pred):
            seg[s][0].append(t)
            seg[s][1].append(p)
        out["by_segment"] = {}
        for s, (ts, ps) in sorted(seg.items()):
            tp = sum(1 for t, p in zip(ts, ps) if t == positive and p == positive)
            pos = sum(1 for t in ts if t == positive)
            tn = sum(1 for t, p in zip(ts, ps) if t != positive and p == t)
            neg = len(ts) - pos
            out["by_segment"][s] = {"n": len(ts), "tp": tp, "P": pos, "tn": tn, "N": neg,
                                    "tpr": tp / pos if pos else None, "tnr": tn / neg if neg else None}
    return out


def disagreement_causes(rows, mechanical=("date_arithmetic", "income_arithmetic")):
    """rows: dicts with 'cause' for every trace where judge and gold differ (abstentions included).
    Returns counts by cause, largest first, and the share whose cause is arithmetic code already does."""
    counts = Counter(r["cause"] for r in rows)
    n = sum(counts.values())
    mech = sum(v for k, v in counts.items() if k in mechanical)
    return {"n": n, "by_cause": dict(counts.most_common()), "mechanical": mech,
            "mechanical_share": mech / n if n else float("nan")}


def construct_profile(base, preserved, changed, edit_types=None):
    """Invariance S: share of verdicts unchanged under edits that keep the construct (rewording,
    turn order, a courtesy phrase in Spanish). Sensitivity R: share of verdicts that change under a
    minimal edit that changes the construct (a relief end date moved across the window, a stated
    change of work added). base, preserved and changed are verdict lists aligned by trace. A judge
    can be very stable and still not notice what changed; report both."""
    s_k = sum(1 for a, b in zip(base, preserved) if a == b)
    r_k = sum(1 for a, b in zip(base, changed) if a != b)
    out = {"S": s_k / len(preserved), "S_k": s_k, "S_n": len(preserved), "S_ci": wilson(s_k, len(preserved)),
           "R": r_k / len(changed), "R_k": r_k, "R_n": len(changed), "R_ci": wilson(r_k, len(changed))}
    if edit_types is not None:
        by = defaultdict(Counter)
        for t, a, b in zip(edit_types, base, changed):
            by[t]["n"] += 1
            by[t]["changed"] += a != b
        out["R_by_type"] = {t: dict(v) for t, v in sorted(by.items())}
    return out


def surface_agreement(feature, judge, gold, positive=POSITIVE):
    """How much a one-feature rule ('fail if the feature is present') reproduces the judge and the
    gold. A rule that reproduces the judge much better than the gold is reading what the judge reads."""
    rule = [positive if f else "pass" for f in feature]
    j = sum(1 for r, v in zip(rule, judge) if r == v)
    g = sum(1 for r, v in zip(rule, gold) if r == v)
    n = len(rule)
    return {"n": n, "judge_k": j, "judge": j / n, "gold_k": g, "gold": g / n, "gap": (j - g) / n}


def escape_bound(missed, n_offers, target=0.005, confidence=0.95):
    """Offers a judge passed that gold says the policy did not permit, per offer, with the exact
    one-sided bound. A judge can gate a rate target only if this bound sits under the target; the
    offers needed to show that with no misses at all is the floor of any trial."""
    ub = upper_bound(missed, n_offers, confidence)
    return {"missed": missed, "n": n_offers, "rate": missed / n_offers, "upper": ub,
            "target": target, "can_gate": ub < target,
            "perfect_upper": upper_bound(0, n_offers, confidence),
            "offers_needed_at_zero": traces_needed(target, 0, confidence)}


def seen_through(true_rate, tpr):
    """The rate a candidate would show through a judge that catches a share tpr of its wrong offers
    and raises no false alarm: the most generous reading a gate could get."""
    return true_rate * tpr


def admit_part(name, table, *, role="order", min_tpr_low=0.80, min_tnr_low=0.90):
    """Chapter 16's floors applied to one part of a split judge."""
    reasons = []
    if table["tpr_ci"][0] < min_tpr_low:
        reasons.append(f"TPR lower bound {table['tpr_ci'][0]:.2f} < {min_tpr_low:.2f}")
    if table["tnr_ci"][0] < min_tnr_low:
        reasons.append(f"TNR lower bound {table['tnr_ci'][0]:.2f} < {min_tnr_low:.2f}")
    return {"part": name, "admit": not reasons, "role": role if not reasons else "none", "reasons": reasons}


def split_verdict(parts, *, gate_needs=None):
    """parts: list of admit_part results. The split may serve a gate only if every part the gate
    needs is admitted; a part that passes keeps its own role and nothing more."""
    gate_needs = gate_needs or [p["part"] for p in parts]
    failed = [p["part"] for p in parts if p["part"] in gate_needs and not p["admit"]]
    return {"gate_allowed": not failed, "failed_parts": failed,
            "admitted": [(p["part"], p["role"]) for p in parts if p["admit"]]}


def decision_record(options):
    """options: dict name -> evidence dict with keys
       'held_out_clean' (bool: scored on traces no rule or design choice was taken from),
       'admitted' (bool), 'replacement' (list of instruments that take over each check, for abandon),
       'weeks' and 'cost' (to have clean evidence).
    Returns, per option, whether the evidence supports it today and why not."""
    out = {}
    for name, ev in options.items():
        why = []
        if name == "abandon":
            if not ev.get("replacement"):
                why.append("no instrument named for the checks the judge would have made")
        else:
            if not ev.get("held_out_clean", False):
                why.append("score is on traces the change was designed from")
            if not ev.get("admitted", False):
                why.append("fails the admission floors")
        out[name] = {"supported_today": not why, "why_not": why,
                     "weeks": ev.get("weeks"), "cost": ev.get("cost")}
    return out
