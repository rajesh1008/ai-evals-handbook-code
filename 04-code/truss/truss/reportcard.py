"""Truss 0.21 (Chapter 18): reportcard.

A Judge Report Card and the corrections that fill it. The module never calls a
model. It takes human labels and judge verdicts and returns the numbers a
compliance officer can be shown: a confusion table (overall and by segment),
Cohen's kappa with a bootstrap interval, a Rogan-Gladen (plug-in) correction of
an observed rate, a prediction-powered estimate with an interval, a leak check
against the set the prompt was tuned on, and admission to the decide role once
the card exists. Drift is a reserved field (Chapter 19).
"""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field

from .adjudication import kappa as _kappa
from .fields import wilson
from .judge import confusion, rates

POSITIVE = "fail"


def cohen_kappa(truth, pred):
    """Cohen's kappa between human labels and judge verdicts."""
    return _kappa(list(truth), list(pred))


def _bootstrap_indices(n, n_boot, seed):
    rng = random.Random(seed)
    for _ in range(n_boot):
        yield [rng.randrange(n) for _ in range(n)]


def kappa_interval(truth, pred, n_boot=2000, seed=2026, alpha=0.05):
    """Point kappa and a percentile bootstrap interval."""
    truth, pred = list(truth), list(pred)
    n = len(truth)
    point = cohen_kappa(truth, pred)
    if n == 0:
        return {"kappa": float("nan"), "ci": (float("nan"), float("nan")), "n_boot": n_boot}
    draws = []
    for idx in _bootstrap_indices(n, n_boot, seed):
        draws.append(cohen_kappa([truth[i] for i in idx], [pred[i] for i in idx]))
    draws.sort()
    lo = draws[int(alpha / 2 * n_boot)]
    hi = draws[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return {"kappa": point, "ci": (lo, hi), "n_boot": n_boot}


def confusion_by_segment(segments, truth, pred, positive=POSITIVE):
    """A confusion table and rates for each segment value."""
    buckets = defaultdict(lambda: {"truth": [], "pred": []})
    for s, t, p in zip(segments, truth, pred):
        buckets[s]["truth"].append(t)
        buckets[s]["pred"].append(p)
    out = {}
    for s, pair in buckets.items():
        cm = confusion(pair["truth"], pair["pred"], positive=positive)
        rt = rates(cm)
        out[s] = {**cm, **rt, "n": len(pair["truth"]),
                  "kappa": cohen_kappa(pair["truth"], pair["pred"])}
    acc = {s: v["tpr"] if False else (v["tp"] + v["tn"]) / v["n"] if v["n"] else float("nan")
           for s, v in out.items()}
    if acc:
        vals = [x for x in acc.values() if x == x]
        out["_max_gap"] = (max(vals) - min(vals)) if vals else float("nan")
    else:
        out["_max_gap"] = float("nan")
    return out


def rogan_gladen(p_obs, sensitivity, specificity):
    """Unbiased prevalence given an observed positive rate, sensitivity (TPR)
    and specificity (TNR). Youden's index (Se + Sp - 1) must be positive."""
    youden = sensitivity + specificity - 1.0
    if youden <= 0:
        raise ValueError("Rogan-Gladen needs sensitivity + specificity > 1")
    p = (p_obs + specificity - 1.0) / youden
    # A noisy sample can push the estimate slightly outside [0, 1]; clip for
    # reporting while leaving the raw value available to the caller.
    return {"p": p, "p_clipped": min(1.0, max(0.0, p)), "youden": youden,
            "p_obs": p_obs, "sensitivity": sensitivity, "specificity": specificity}


def _se_sp(truth, pred, positive=POSITIVE):
    cm = confusion(list(truth), list(pred), positive=positive)
    rt = rates(cm)
    return rt["tpr"], rt["tnr"], cm, rt


def rogan_gladen_interval(truth, pred, unlabeled_pred, n_boot=2000, seed=2026,
                          alpha=0.05, positive=POSITIVE):
    """Percentile bootstrap of the Rogan-Gladen estimate. Resamples the
    labelled calibration set (for sensitivity and specificity) and the
    unlabelled judge verdicts (for the observed rate), matching the two-source
    uncertainty of the plug-in correction."""
    truth, pred, unlabeled_pred = list(truth), list(pred), list(unlabeled_pred)
    se, sp, cm, rt = _se_sp(truth, pred, positive=positive)
    p_obs = sum(p == positive for p in unlabeled_pred) / len(unlabeled_pred) if unlabeled_pred else float("nan")
    point = rogan_gladen(p_obs, se, sp)
    n, N = len(truth), len(unlabeled_pred)
    draws = []
    rng = random.Random(seed)
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        jdx = [rng.randrange(N) for _ in range(N)] if N else []
        se_b, sp_b, _, _ = _se_sp([truth[i] for i in idx], [pred[i] for i in idx], positive=positive)
        p_obs_b = (sum(unlabeled_pred[j] == positive for j in jdx) / N) if N else float("nan")
        try:
            draws.append(rogan_gladen(p_obs_b, se_b, sp_b)["p"])
        except ValueError:
            continue
    draws.sort()
    if not draws:
        ci = (float("nan"), float("nan"))
    else:
        lo = draws[int(alpha / 2 * len(draws))]
        hi = draws[min(len(draws) - 1, int((1 - alpha / 2) * len(draws)))]
        ci = (lo, hi)
    return {**point, "ci": ci, "n_boot": n_boot, "kept": len(draws),
            "cm": cm, "rates": rt, "n_labeled": n, "n_unlabeled": N}


def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def _var(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def as_indicator(values, positive=POSITIVE):
    return [1.0 if v == positive else 0.0 for v in values]


def ppi(y_labeled, f_labeled, f_unlabeled):
    """Prediction-powered estimate of a mean (a rate, when the inputs are 0/1).

    theta_hat = mean(y) - mean(f_on_labeled) + mean(f_on_unlabeled).
    No assumption is made on how f was produced.
    """
    y = list(y_labeled)
    f_n = list(f_labeled)
    f_N = list(f_unlabeled)
    if not y or len(y) != len(f_n):
        raise ValueError("labelled gold and labelled predictions must be the same non-empty length")
    rectifier = _mean(y) - _mean(f_n)
    return {"p": rectifier + _mean(f_N) if f_N else rectifier,
            "human": _mean(y), "judge_labeled": _mean(f_n),
            "judge_unlabeled": _mean(f_N) if f_N else float("nan"),
            "rectifier": rectifier, "n": len(y), "N": len(f_N)}


def ppi_interval(y_labeled, f_labeled, f_unlabeled, z=1.96):
    """Asymptotic interval from Var(Y - f(X))/n + Var(f(X))/N on the unlabelled
    predictions. This is the classical prediction-powered variance for a mean."""
    est = ppi(y_labeled, f_labeled, f_unlabeled)
    residual = [y - f for y, f in zip(y_labeled, f_labeled)]
    n, N = est["n"], est["N"]
    var = _var(residual) / n + (_var(f_unlabeled) / N if N else 0.0)
    se = math.sqrt(var) if var >= 0 else float("nan")
    return {**est, "se": se, "ci": (est["p"] - z * se, est["p"] + z * se), "z": z}


def human_only_interval(y_labeled, z=1.96):
    """The human-only rate and a Wald interval, for width comparison with PPI.
    Wilson is preferred for the published human-only bound; Wald sits next to
    PPI because both are asymptotic."""
    y = list(y_labeled)
    p = _mean(y)
    n = len(y)
    se = math.sqrt(p * (1 - p) / n) if n else float("nan")
    return {"p": p, "se": se, "ci": (p - z * se, p + z * se), "n": n,
            "wilson": wilson(int(round(p * n)), n) if n else (float("nan"), float("nan"))}


def leak_ids(val_ids, reserved_ids):
    """Trace IDs that appear in both the validation set and a reserved set
    (the development traces the prompt was tuned on, or the rubric examples)."""
    return sorted(set(val_ids) & set(reserved_ids))


def kind_mix(kinds):
    """A categorical distribution over kinds, as counts and shares."""
    c = Counter(kinds)
    n = sum(c.values())
    return {k: {"n": v, "share": v / n if n else float("nan")} for k, v in sorted(c.items())} | {"_n": n}


def total_variation(mix_a, mix_b):
    """Total variation distance between two kind_mix results (half L1)."""
    keys = (set(mix_a) | set(mix_b)) - {"_n"}
    return 0.5 * sum(abs(mix_a.get(k, {}).get("share", 0.0) - mix_b.get(k, {}).get("share", 0.0))
                     for k in keys)


def invariance_split(y, f, unlabeled_f, key):
    """Recompute PPI inside each value of `key` (for example a length bin).
    An estimate that measures fee correctness should not jump when the split
    is something the card does not read."""
    buckets = defaultdict(lambda: {"y": [], "f": []})
    for k, yi, fi in zip(key, y, f):
        buckets[k]["y"].append(yi)
        buckets[k]["f"].append(fi)
    out = {}
    for k, pair in buckets.items():
        if not pair["y"]:
            continue
        out[k] = ppi(pair["y"], pair["f"], unlabeled_f)
    ps = [v["p"] for v in out.values() if v["p"] == v["p"]]
    out["_range"] = (max(ps) - min(ps)) if len(ps) >= 2 else float("nan")
    out["_n_groups"] = len(ps)
    return out


def sensitivity_flip(y, f, unlabeled_f, n_flip=5, seed=2026, toward=1.0):
    """Flip `n_flip` labelled gold values toward `toward` (1 = fail). A working
    estimator must move; an estimator that ignores the gold will not."""
    y = list(y)
    f = list(f)
    baseline = ppi(y, f, unlabeled_f)
    rng = random.Random(seed)
    candidates = [i for i, yi in enumerate(y) if yi != toward]
    if not candidates:
        return {"baseline": baseline, "perturbed": baseline, "moved": 0.0, "n_flip": 0}
    rng.shuffle(candidates)
    take = candidates[: min(n_flip, len(candidates))]
    y2 = list(y)
    for i in take:
        y2[i] = toward
    perturbed = ppi(y2, f, unlabeled_f)
    return {"baseline": baseline, "perturbed": perturbed,
            "moved": perturbed["p"] - baseline["p"], "n_flip": len(take)}


@dataclass
class ReportCard:
    """The Judge Report Card (Signature 5). Drift is reserved for Chapter 19."""
    judge: str
    metric_card: str
    n_labeled: int
    n_judged: int
    confusion: dict
    rates: dict
    kappa: float
    kappa_ci: tuple
    raw_rate: float
    raw_ci: tuple
    rg: dict
    ppi: dict
    segments: dict
    leak: list
    kind_tv_vs_reserved: float
    invariance_range: float
    sensitivity_moved: float
    drift: dict = field(default_factory=lambda: {
        "status": "not_yet_measured",
        "owner": "Chapter 19",
    })
    role: str = "none"
    admitted: bool = False
    reasons: list = field(default_factory=list)

    def as_dict(self):
        d = asdict(self)
        return d


def build_card(truth, pred, unlabeled_pred, *, judge, metric_card,
               segments=None, val_ids=None, reserved_ids=None,
               val_kinds=None, reserved_kinds=None,
               invariance_key=None, n_boot=2000, seed=2026,
               positive=POSITIVE):
    """Assemble a Judge Report Card from labelled pairs and a larger judged set."""
    truth, pred, unlabeled_pred = list(truth), list(pred), list(unlabeled_pred)
    cm = confusion(truth, pred, positive=positive)
    rt = rates(cm)
    kap = kappa_interval(truth, pred, n_boot=n_boot, seed=seed)
    raw_k = sum(p == positive for p in unlabeled_pred)
    raw_n = len(unlabeled_pred)
    raw = raw_k / raw_n if raw_n else float("nan")
    raw_ci = wilson(raw_k, raw_n) if raw_n else (float("nan"), float("nan"))
    rg = rogan_gladen_interval(truth, pred, unlabeled_pred, n_boot=n_boot, seed=seed,
                               positive=positive)
    y = as_indicator(truth, positive=positive)
    f_n = as_indicator(pred, positive=positive)
    f_N = as_indicator(unlabeled_pred, positive=positive)
    pp = ppi_interval(y, f_n, f_N)
    segs = confusion_by_segment(segments, truth, pred, positive=positive) if segments is not None else {}
    leaked = leak_ids(val_ids or [], reserved_ids or [])
    tv = total_variation(kind_mix(val_kinds or []), kind_mix(reserved_kinds or [])) if (val_kinds and reserved_kinds) else float("nan")
    inv = invariance_split(y, f_n, f_N, invariance_key) if invariance_key is not None else {"_range": float("nan")}
    sens = sensitivity_flip(y, f_n, f_N, n_flip=5, seed=seed)
    return ReportCard(
        judge=judge, metric_card=metric_card,
        n_labeled=len(truth), n_judged=raw_n,
        confusion=cm, rates=rt,
        kappa=kap["kappa"], kappa_ci=kap["ci"],
        raw_rate=raw, raw_ci=raw_ci,
        rg=rg, ppi=pp, segments=segs, leak=leaked,
        kind_tv_vs_reserved=tv,
        invariance_range=inv.get("_range", float("nan")),
        sensitivity_moved=sens["moved"],
    )


def admit_decide(card: ReportCard, *, min_kappa=0.80, min_tnr_low=0.90,
                 max_segment_gap=0.20, min_kind_tv=0.10):
    """Whether the judge may enter the decide role (and so the gate tier) on
    the strength of this card. The Chapter 16 TPR floor of 0.80 on a Wilson
    lower bound is not re-applied here when the labelled set has few
    positives: that bound is then too wide to decide anything, and the
    corrected rate plus TNR carry the claim. A leak, or a kind-mix that
    clones the reserved (tuning) distribution (total variation below
    `min_kind_tv`), refuses admission."""
    reasons = []
    if card.leak:
        reasons.append(f"validation overlaps reserved IDs: {', '.join(card.leak[:8])}")
    if card.kind_tv_vs_reserved == card.kind_tv_vs_reserved and card.kind_tv_vs_reserved < min_kind_tv:
        reasons.append(f"validation kind-mix too close to reserved set (TV {card.kind_tv_vs_reserved:.3f})")
    if card.kappa < min_kappa:
        reasons.append(f"kappa {card.kappa:.3f} < {min_kappa:.2f}")
    tnr_low = card.rates.get("tnr_ci", (float("nan"), float("nan")))[0]
    if tnr_low == tnr_low and tnr_low < min_tnr_low:
        reasons.append(f"TNR lower bound {tnr_low:.2f} < {min_tnr_low:.2f}")
    gap = card.segments.get("_max_gap", float("nan")) if card.segments else float("nan")
    if gap == gap and gap > max_segment_gap:
        reasons.append(f"segment accuracy gap {gap:.2f} > {max_segment_gap:.2f}")
    if card.sensitivity_moved == 0:
        reasons.append("sensitivity test did not move the estimate")
    admitted = not reasons
    card.reasons = reasons
    card.admitted = admitted
    card.role = "decide" if admitted else "order"
    return {"admit": admitted, "role": card.role, "reasons": reasons,
            "judge": card.judge, "metric_card": card.metric_card}
