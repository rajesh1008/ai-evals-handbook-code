"""Truss 0.19 (Chapter 16): judge. A model judge as a measured instrument.

The module never calls a model. It renders the prompt from a judge specification, parses what comes
back, keeps the judge's own eval set honest (dev and test kept apart, rules written from dev only),
scores the judge against adjudicated labels, measures repeat flips and pairwise position effects,
prices a month of judging against a month of reading, and decides whether the judge may enter the
monitoring tier, and in which role.
"""
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .adjudication import kappa
from .fields import wilson

OUTCOMES = ("pass", "fail", "cannot_tell")


@dataclass
class JudgeSpec:
    card: str                      # metric card the judge reads for, e.g. "MC-02"
    card_version: str              # e.g. "1.1"
    question: str                  # the card's question, verbatim
    rules: list                    # numbered decision rules, written from dev traces only
    inputs: tuple = ("question", "tool_span", "reply")
    critique_first: bool = True
    model: str = ""
    version: str = "v1"
    outcomes: tuple = OUTCOMES


class MissingInput(ValueError):
    pass


def render(spec: JudgeSpec, fields_: dict) -> str:
    """The prompt for one trace. Refuses when an input the card depends on is missing, so a judge
    cannot quietly read a reply without the span it is meant to check it against."""
    missing = [k for k in spec.inputs if not fields_.get(k)]
    if missing:
        raise MissingInput(f"{spec.card} judge needs {', '.join(missing)}")
    rules = "\n".join(f"{i}. {r}" for i, r in enumerate(spec.rules, 1))
    trace = "\n".join(f"{k}: {fields_[k]}" for k in spec.inputs)
    opts = " | ".join(f'"{o}"' for o in spec.outcomes)
    tail = ("First write a critique of at most four sentences. Then, on the last line, output JSON only: "
            if spec.critique_first else "Answer with JSON only, no other text: ")
    return (f"Check {spec.card} v{spec.card_version}.\nQuestion: {spec.question}\n\nHow to decide:\n{rules}\n\n"
            f"{trace}\n\n{tail}{{\"verdict\": {opts}}}")


def parse(text, outcomes=OUTCOMES, key="verdict"):
    """The verdict in the last JSON object of the reply, or 'unparsed'. A verdict outside the
    allowed outcomes is 'unparsed' too; it is never coerced."""
    for s in reversed(re.findall(r"\{[^{}]*\}", text or "")):
        try:
            v = str(json.loads(s).get(key, "")).strip().lower()
        except (json.JSONDecodeError, AttributeError):
            continue
        if v:
            return v if v in [o.lower() for o in outcomes] else "unparsed"
    return "unparsed"


# ------------------------------------------------------------------ the judge's own eval set

def split(items, kind, every=3, offset=0):
    """Dev and test, stratified by kind: within each kind, every `every`-th item (from `offset`) goes
    to dev. Deterministic given the order of items."""
    dev, test, seen = [], [], Counter()
    for it in items:
        k = kind(it)
        (dev if (seen[k] - offset) % every == 0 else test).append(it)
        seen[k] += 1
    return dev, test


class Leak(ValueError):
    pass


def guard(rule_sources, test_ids):
    """Rules and worked examples must come from dev. Raises with the leaked IDs otherwise."""
    leaked = sorted(set(rule_sources) & set(test_ids))
    if leaked:
        raise Leak(f"rule or example drawn from test traces: {', '.join(leaked)}")
    return True


# ------------------------------------------------------------------ scoring against labels

def confusion(truth, pred, positive="fail"):
    """Counts with the positive class 'fail' (a wrong reply). cannot_tell and unparsed are kept
    apart and counted as misses in the rates, because neither orders a reading."""
    c = Counter()
    for t, p in zip(truth, pred):
        if p not in ("pass", "fail"):
            c["abstain_" + ("pos" if t == positive else "neg")] += 1
        elif t == positive:
            c["tp" if p == positive else "fn"] += 1
        else:
            c["tn" if p != positive else "fp"] += 1
    return {k: c.get(k, 0) for k in ("tp", "fn", "fp", "tn", "abstain_pos", "abstain_neg")}


def rates(cm):
    P = cm["tp"] + cm["fn"] + cm["abstain_pos"]
    N = cm["tn"] + cm["fp"] + cm["abstain_neg"]
    out = {"P": P, "N": N,
           "tpr": cm["tp"] / P if P else float("nan"), "tpr_ci": wilson(cm["tp"], P),
           "tnr": cm["tn"] / N if N else float("nan"), "tnr_ci": wilson(cm["tn"], N)}
    called = cm["tp"] + cm["fp"]
    out["precision"] = cm["tp"] / called if called else float("nan")
    return out


def agreement_kappa(truth, pred):
    """Cohen's kappa between the judge and the adjudicated labels over all outcomes."""
    return kappa(list(truth), list(pred))


def by_kind(kinds, truth, pred):
    rows = defaultdict(Counter)
    for k, t, p in zip(kinds, truth, pred):
        rows[k]["right" if p == t else "wrong"] += 1
    return {k: dict(v) for k, v in rows.items()}


# ------------------------------------------------------------------ repeats and pairs

def flips(runs):
    """runs: list of lists of verdicts over the same items. Share of items whose verdict was not
    identical across every run, and the items' indices."""
    idx = [i for i, vs in enumerate(zip(*runs)) if len(set(vs)) > 1]
    n = len(runs[0]) if runs else 0
    return {"items": n, "flipped": len(idx), "rate": len(idx) / n if n else float("nan"), "where": idx}


def majority(runs, tie="cannot_tell"):
    out = []
    for vs in zip(*runs):
        (top, k), *rest = Counter(vs).most_common() + [(None, 0)]
        out.append(top if k > len(vs) / 2 else tie)
    return out


def pair_outcome(first_order, swapped_order):
    """first_order: winner when the original reply is shown as A ('A', 'B' or 'tie'); swapped_order:
    winner with the original shown as B. Returns 'original', 'other', 'tie' or 'position' (the judge
    picked the same slot both times, so its choice followed the slot, not the reply)."""
    m1 = {"A": "original", "B": "other", "tie": "tie"}.get(first_order, "unparsed")
    m2 = {"B": "original", "A": "other", "tie": "tie"}.get(swapped_order, "unparsed")
    if "unparsed" in (m1, m2):
        return "unparsed"
    return m1 if m1 == m2 else "position"


# ------------------------------------------------------------------ cost, latency and the month

def call_cost(tokens_in, tokens_out, price_in, price_out):
    """US dollars, prices per million tokens."""
    return (tokens_in * price_in + tokens_out * price_out) / 1e6


def percentile(xs, q):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    i = (len(xs) - 1) * q
    lo, hi = math.floor(i), math.ceil(i)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def month(traces, cost_per_trace, judge_fail_rate, read_minutes=2.0, reader_rate=60.0):
    """A month of judging every trace and reading what the judge orders, against reading every trace."""
    judge = traces * cost_per_trace
    ordered = traces * judge_fail_rate
    read_ordered = ordered * read_minutes / 60 * reader_rate
    read_all = traces * read_minutes / 60 * reader_rate
    return {"judge_cost": judge, "ordered_reads": ordered, "read_ordered_cost": read_ordered,
            "judge_plus_reads": judge + read_ordered, "read_everything": read_all}


# ------------------------------------------------------------------ entry to a tier

def admit(spec: JudgeSpec, test_rates, *, role, tested_on_test=True, report_card=None,
          min_tpr_low=0.80, min_tnr_low=0.90):
    """Whether the judge may enter the monitoring tier, and in which role (Chapter 10's decide, order
    or none). Without a Judge Report Card (Chapter 18) a judge may at most order readings; it never
    decides. Bounds are on the lower Wilson limits from the held-out test set."""
    reasons = []
    if not tested_on_test:
        reasons.append("no held-out test run")
    if test_rates["tpr_ci"][0] < min_tpr_low:
        reasons.append(f"TPR lower bound {test_rates['tpr_ci'][0]:.2f} < {min_tpr_low:.2f}")
    if test_rates["tnr_ci"][0] < min_tnr_low:
        reasons.append(f"TNR lower bound {test_rates['tnr_ci'][0]:.2f} < {min_tnr_low:.2f}")
    if role == "decide" and report_card is None:
        reasons.append("role decide needs a Judge Report Card")
    if role not in ("decide", "order", "none"):
        reasons.append(f"unknown role {role}")
    return {"admit": not reasons, "role": role if not reasons else "none", "card": f"{spec.card} v{spec.card_version}",
            "reasons": reasons}
