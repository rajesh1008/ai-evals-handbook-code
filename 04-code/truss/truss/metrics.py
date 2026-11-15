"""Chapter 8: metrics derived from failure modes (the release the book calls Truss v1).

A metric is a card: one yes/no question asked of one conversation, the population it is
asked of, the failure modes it measures, the instrument that answers it, the tier that says
what a number can decide, and an owner. The registry enforces the book's rule: no metric in
the gate or monitor tier unless every failure mode it cites is active in the taxonomy and has
appeared in at least one named trace. Measures with no failure mode behind them (CSAT, reply
length) may be kept as signals in the inform tier; they can never gate or alert.

Outcomes per conversation: pass, fail, deferred (the reply correctly hands the question to a
person), cannot_tell (the trace lacks what the question needs). A card says where deferred
counts; cannot_tell is always reported and never silently dropped.
Plain Python plus scipy (already a Truss dependency).
"""
import math
from dataclasses import asdict, dataclass, field

from scipy.stats import binomtest, spearmanr

from .rates import upper_bound, wilson

KINDS = ("code", "reference", "judge", "signal")
TIERS = ("gate", "monitor", "inform")
OUTCOMES = ("pass", "fail", "deferred", "cannot_tell")
RULES = ("", "no_new_fail", "paired")


@dataclass
class Card:
    id: str
    name: str
    modes: tuple                    # FM codes; empty only for an inform-tier signal
    question: str                   # the binary question asked of one conversation
    population: str                 # who is in the denominator, exclusions declared
    kind: str                       # code, reference, judge (human-read until Chapter 16), signal
    tier: str                       # gate, monitor, inform
    owner: str
    flows: tuple = ()
    instrument: str = ""            # the check or the reading that answers the question
    validated: str = ""             # agreement evidence for the instrument; required for a gate
    deferred_as: str = "excluded"   # excluded, fail or pass
    target: float = None            # long-run aim (a rate), reported with its bound
    alert: float = None             # monitor tier: weekly rate that pages the owner
    rule: str = ""                  # gate tier: no_new_fail or paired
    weakness: str = ""              # what the metric is known to reward wrongly
    version: str = "1.0"
    history: list = field(default_factory=list)

    def __post_init__(self):
        self.modes, self.flows = tuple(self.modes), tuple(self.flows)
        if self.kind not in KINDS or self.tier not in TIERS or self.rule not in RULES:
            raise ValueError(f"{self.id}: kind/tier/rule {self.kind}/{self.tier}/{self.rule}")
        if self.deferred_as not in ("excluded", "fail", "pass"):
            raise ValueError(f"{self.id}: deferred_as {self.deferred_as!r}")
        if self.tier == "gate" and not self.rule:
            raise ValueError(f"{self.id}: a gate metric needs a rule")

    def amend(self, date, note, **changes):
        """Change a card: minor version up, dated note kept."""
        for k, v in changes.items():
            setattr(self, k, tuple(v) if k in ("modes", "flows") else v)
        major, minor = self.version.split(".")
        self.version = f"{major}.{int(minor) + 1}"
        self.history.append((date, self.version, note))
        return self


class Refused(ValueError):
    pass


class Registry:
    """taxonomy: {code: status}; evidence: {code: [trace ids where the mode was seen]}."""

    def __init__(self, taxonomy, evidence, digest=""):
        self.taxonomy, self.evidence, self.digest = dict(taxonomy), dict(evidence), digest
        self.cards, self.refused = {}, []

    def check(self, card):
        reasons = []
        if not card.modes:
            if card.tier != "inform" or card.kind != "signal":
                reasons.append("no failure mode: only an inform-tier signal may have none")
        for m in card.modes:
            if self.taxonomy.get(m) != "active":
                reasons.append(f"{m} is {self.taxonomy.get(m, 'not in the taxonomy')}")
            elif not self.evidence.get(m):
                reasons.append(f"{m} has no trace evidence")
        if card.tier == "gate" and not card.validated:
            reasons.append("gate tier needs a validated instrument")
        dup = [c.id for c in self.cards.values() if c.id != card.id and set(c.modes) == set(card.modes) and c.modes]
        if dup:
            reasons.append(f"same modes as {dup[0]}: one metric per failure mode")
        return reasons

    def add(self, card):
        reasons = self.check(card)
        if reasons:
            self.refused.append((card.id, card.name, reasons))
            raise Refused(f"{card.id} {card.name}: " + "; ".join(reasons))
        self.cards[card.id] = card
        return card

    def try_add(self, card):
        try:
            return self.add(card)
        except Refused:
            return None

    def by_tier(self):
        out = {t: [] for t in TIERS}
        for c in self.cards.values():
            out[c.tier].append(c.id)
        return out

    def unmetered(self):
        """Active modes no card measures."""
        seen = {m for c in self.cards.values() for m in c.modes}
        return sorted(m for m, s in self.taxonomy.items() if s == "active" and m not in seen)


def measure(card, outcomes, confidence=0.95):
    """outcomes: list of pass/fail/deferred/cannot_tell. Returns counts, rate, Wilson, one-sided bound."""
    bad = [o for o in outcomes if o not in OUTCOMES]
    if bad:
        raise ValueError(f"unknown outcomes {set(bad)}")
    c = {o: outcomes.count(o) for o in OUTCOMES}
    k = c["fail"] + (c["deferred"] if card.deferred_as == "fail" else 0)
    n = c["pass"] + c["fail"] + (c["deferred"] if card.deferred_as != "excluded" else 0)
    lo, hi = wilson(k, n)
    return {"card": card.id, "version": card.version, "fail": k, "n": n, "rate": k / n if n else 0.0,
            "wilson": (lo, hi), "upper": upper_bound(k, n, confidence) if n else 1.0,
            "deferred": c["deferred"], "cannot_tell": c["cannot_tell"],
            "meets_target": None if card.target is None else upper_bound(k, n, confidence) < card.target}


def length_table(rows, score, failed, length, bands):
    """Length-stratified view of a score: per band, n, mean score, failure rate.
    rows: dicts; score/failed/length: keys; bands: [(label, lo, hi)] with lo <= x < hi."""
    out = []
    for label, lo, hi in bands:
        b = [r for r in rows if lo <= r[length] < hi]
        k = sum(1 for r in b if r[failed])
        out.append({"band": label, "n": len(b), "mean_score": sum(r[score] for r in b) / len(b) if b else float("nan"),
                    "fail": k, "fail_rate": k / len(b) if b else float("nan"), "wilson": wilson(k, len(b))})
    return out


def length_bias(rows, score, failed, length):
    """Flags a score that tracks length more than it tracks the failure it claims to measure."""
    s = [r[score] for r in rows]
    rho_len = spearmanr(s, [r[length] for r in rows]).statistic
    rho_fail = spearmanr(s, [-int(r[failed]) for r in rows]).statistic
    return {"rho_length": float(rho_len), "rho_correct": float(rho_fail),
            "flag": abs(rho_len) > abs(rho_fail)}


def composite(rates, weights):
    """Weighted mean of pass rates with each part's contribution, the arithmetic a dashboard hides."""
    tot = sum(weights.values())
    parts = {k: weights[k] / tot * rates[k] for k in weights}
    return sum(parts.values()), parts


def move_needed(weights, delta=0.01):
    """Change in each part's pass rate that alone moves the composite by delta."""
    tot = sum(weights.values())
    return {k: delta * tot / w for k, w in weights.items()}


def paired(base, cand):
    """base/cand: {trace: outcome}. Newly failing (b) and newly passing (c) traces, by id."""
    b = sorted(t for t in base if base[t] != "fail" and cand[t] == "fail")
    c = sorted(t for t in base if base[t] == "fail" and cand[t] != "fail")
    return b, c


def before_after(cards, base, cand, alpha=0.05):
    """cards: [Card]; base/cand: {card id: {trace: outcome}} on the same replay set.
    One row per card; gate cards get a decision under their rule."""
    rows, holds = [], []
    for card in cards:
        m0, m1 = measure(card, list(base[card.id].values())), measure(card, list(cand[card.id].values()))
        b, c = paired(base[card.id], cand[card.id])
        verdict = ""
        if card.tier == "gate":
            if card.rule == "no_new_fail" and b:
                verdict = "hold"
            elif card.rule == "paired" and len(b) + len(c) and \
                    binomtest(len(b), len(b) + len(c), 0.5, alternative="greater").pvalue < alpha:
                verdict = "hold"
            else:
                verdict = "pass"
            if verdict == "hold":
                holds.append(f"{card.id}: {len(b)} newly fail ({', '.join(b[:4])}{'...' if len(b) > 4 else ''})")
        rows.append({"card": card.id, "name": card.name, "tier": card.tier, "before": (m0["fail"], m0["n"]),
                     "after": (m1["fail"], m1["n"]), "before_rate": m0["rate"], "after_rate": m1["rate"],
                     "after_wilson": m1["wilson"], "newly_fail": b, "newly_pass": c, "verdict": verdict})
    return rows, ("hold" if holds else "ship"), holds


def weighted_kappa(a, b, cats=(1, 2, 3, 4, 5)):
    """Quadratic-weighted kappa for two readers' ordinal scores."""
    n, k = len(a), len(cats)
    idx = {c: i for i, c in enumerate(cats)}
    o = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        o[idx[x]][idx[y]] += 1
    ra = [sum(r) for r in o]
    cb = [sum(o[i][j] for i in range(k)) for j in range(k)]
    w = lambda i, j: (i - j) ** 2 / (k - 1) ** 2
    num = sum(w(i, j) * o[i][j] for i in range(k) for j in range(k))
    den = sum(w(i, j) * ra[i] * cb[j] / n for i in range(k) for j in range(k))
    return 1 - num / den if den else 1.0


def to_markdown(card, result=None):
    lines = [f"### {card.id} {card.name} (card v{card.version})", "", "| Field | Value |", "|---|---|"]
    d = asdict(card)
    for key in ("modes", "question", "population", "kind", "instrument", "validated", "deferred_as", "tier",
                "rule", "target", "alert", "owner", "weakness"):
        v = d[key]
        if v in ("", None, ()):
            continue
        lines.append(f"| {key} | {', '.join(v) if isinstance(v, (list, tuple)) else v} |")
    if result:
        lo, hi = result["wilson"]
        lines.append(f"| last measured | {result['fail']} in {result['n']} ({result['rate']:.1%}, Wilson "
                     f"{lo:.1%} to {hi:.1%}); deferred {result['deferred']}; cannot tell {result['cannot_tell']} |")
    for date, v, note in card.history:
        lines.append(f"| history | {date} v{v}: {note} |")
    return "\n".join(lines)
