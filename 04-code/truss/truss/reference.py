"""Chapter 10: reference-based metrics and their limits (Truss 0.13).

Two kinds of reference, kept apart:
  reference values  a field from a system of record (the fee tool's amount, the title office's
                    date) compared with a claim extracted from the reply. These can decide.
  reference texts   a written answer compared with the reply by overlap or similarity (exact
                    match, BLEU, ROUGE-L, BERTScore, embedding cosine). These can order reading.

What is here, in plain Python (scipy already a dependency):
  normalise, exact_match, token_f1, rouge_l        text overlap without extra packages
  auc, auc_interval                                does a score separate wrong from right
  recall_at_k, gate_cost                           what reading the k lowest buys; what a cut-off costs
  supported_role                                   the strictest job a validation supports
  RefSet, stale                                    versioned reference texts tied to their source
  FactKey, partial_credit                          fact-level comparison with make-or-break facts
Wrappers for BLEU, chrF and BERTScore live in the Chapter 10 lab, which installs their packages.
"""
import hashlib
import random
import re
from dataclasses import dataclass, field

_WORD = re.compile(r"[a-z0-9$]+(?:[.,][0-9]+)*")


def normalise(text):
    return " ".join(_WORD.findall(text.lower()))


def exact_match(reply, ref):
    return float(normalise(reply) == normalise(ref))


def token_f1(reply, ref):
    a, b = normalise(reply).split(), normalise(ref).split()
    if not a or not b:
        return float(a == b)
    common = sum(min(a.count(w), b.count(w)) for w in set(a))
    if not common:
        return 0.0
    p, r = common / len(a), common / len(b)
    return 2 * p * r / (p + r)


def _lcs(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def rouge_l(reply, ref):
    """ROUGE-L F1 on normalised tokens (no stemming)."""
    a, b = normalise(reply).split(), normalise(ref).split()
    if not a or not b:
        return 0.0
    k = _lcs(a, b)
    if not k:
        return 0.0
    p, r = k / len(a), k / len(b)
    return 2 * p * r / (p + r)


def auc(scores_right, scores_wrong):
    """Probability that a right reply scores above a wrong one (ties count half)."""
    if not scores_right or not scores_wrong:
        raise ValueError("need both groups")
    wins = 0.0
    for r in scores_right:
        for w in scores_wrong:
            wins += 1.0 if r > w else (0.5 if r == w else 0.0)
    return wins / (len(scores_right) * len(scores_wrong))


def auc_interval(scores_right, scores_wrong, reps=2000, seed=2026, level=0.95):
    """Percentile bootstrap, resampling each group separately."""
    g = random.Random(seed)
    vals = sorted(auc([g.choice(scores_right) for _ in scores_right],
                      [g.choice(scores_wrong) for _ in scores_wrong]) for _ in range(reps))
    lo, hi = int((1 - level) / 2 * reps), int((1 + level) / 2 * reps) - 1
    return vals[lo], vals[hi]


def recall_at_k(scores, wrong, k):
    """Read the k lowest-scoring replies: how many of the wrong ones are among them."""
    order = sorted(range(len(scores)), key=lambda i: (scores[i], i))[:k]
    return sum(wrong[i] for i in order)


def gate_cost(scores, wrong, catch):
    """Cut-off that flags at least `catch` wrong replies; returns (cut, wrong flagged, right flagged)."""
    pairs = sorted(zip(scores, wrong))
    caught = 0
    for i, (s, w) in enumerate(pairs):
        caught += w
        if caught >= catch:
            flagged = pairs[:i + 1]
            return s, caught, sum(1 for _, x in flagged if not x)
    return None, caught, sum(1 for _, x in pairs if not x)


def supported_role(checks):
    """The strictest job a validation supports, under Harbor Lending's May 2027 rule.
    checks: one (auc_low, wrong_caught, n_wrong, right_flagged, n_right) per labelled set, the
    cut-off fixed on the first set and carried unchanged to the others.

    decide  (may answer a gate or monitor card): two or more labelled sets, ten or more wrong
            cases in each, and on every set the cut-off catches 95% of the wrong replies while
            flagging at most 5% of the right ones
    order   (may sort a reading queue): the AUC's lower bound above 0.5 on every set
    none    otherwise
    """
    decide = len(checks) >= 2 and all(nw >= 10 and caught >= 0.95 * nw and flagged <= 0.05 * nr
                                      for _, caught, nw, flagged, nr in checks)
    if decide:
        return "decide"
    return "order" if all(c[0] > 0.5 for c in checks) else "none"


@dataclass
class RefSet:
    """Reference texts by situation, tied to the policy document they were written from."""
    name: str
    author: str
    written: str
    source: str                   # policy document ID, e.g. fee-schedule-2026-03
    texts: dict                   # situation -> template with {fields}
    version: str = "1.0"
    covers: tuple = field(default=())

    def __post_init__(self):
        self.covers = tuple(sorted(self.texts))

    def digest(self):
        body = "\n".join(f"{k}={self.texts[k]}" for k in self.covers) + self.source
        return hashlib.sha256(body.encode()).hexdigest()[:12]

    def text(self, situation, **facts):
        if situation not in self.texts:
            raise KeyError(f"{self.name} has no reference for {situation!r}")
        return self.texts[situation].format(**facts)


def stale(refset, current_sources, situations=()):
    """Reasons a reference set cannot be trusted today: retired source, missing situations."""
    reasons = []
    if refset.source not in current_sources:
        reasons.append(f"written from {refset.source}, not a current source")
    missing = sorted(set(situations) - set(refset.covers))
    if missing:
        reasons.append("no reference for " + ", ".join(missing))
    return reasons


@dataclass
class FactKey:
    name: str
    critical: bool = False        # make-or-break: wrong here fails the reply whatever else is right


def partial_credit(claimed, truth, keys):
    """Per-fact comparison. Returns (share of facts right, failed critical facts, per-fact dict).
    A fact the reply does not state is None and counts as not right; a critical fact the reply
    leaves unstated is not a failure unless truth requires it to be stated (truth value not None)."""
    per, crit = {}, []
    for k in keys:
        c, t = claimed.get(k.name), truth.get(k.name)
        ok = (c == t) if t is not None else (c is None)
        per[k.name] = ok
        if k.critical and not ok and not (c is None and t is None):
            crit.append(k.name)
    share = sum(per.values()) / len(keys) if keys else 0.0
    return share, crit, per
