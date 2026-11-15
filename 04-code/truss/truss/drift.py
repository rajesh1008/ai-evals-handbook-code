"""Truss 0.22 (Chapter 19): drift. Two-track rolling agreement monitoring,
alert rules, judge version records, and a change-control gate for rubric revisions.

The module never calls a model. It scores already-collected verdicts against
gold, splits a frozen canary from a fresh weekly sample, raises alerts against
signed cut-offs, pins a judge version as a content digest, and holds a rubric
revision that deletes or silently rewrites a label-derived check.

Chapter 18 (in flight when this shipped) is expected to take 0.21.0 for the
Judge Report Card; this release leaves that number unused.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from .adjudication import kappa as _kappa
from .fields import wilson
from .judge import agreement_kappa, confusion, rates


# Harbor's default thresholds, signed when fee-judge-v1 entered the gate
# (Chapter 18's promotion, assumed Monday 15 November 2027). A drop is
# measured against the rolling median of prior weeks on the same track.
THRESHOLDS = {
    "kappa_floor_flag": 0.75,
    "kappa_floor_fail": 0.70,
    "drop_flag": 0.10,
    "drop_fail": 0.15,
    "track_gap_flag": 0.15,
}


def _finite(x):
    return x == x


def week_report(truth, pred, positive="fail"):
    """Agreement, Cohen's kappa, TPR and TNR for one labelled draw.

    Abstentions are counted as misses in the rates (same rule as
    ``truss.judge.rates``). Kappa is computed over the raw outcome
    strings, so an abstention is a disagreement.
    """
    truth = list(truth)
    pred = list(pred)
    if len(truth) != len(pred):
        raise ValueError("truth and pred must be the same length")
    n = len(truth)
    cm = confusion(truth, pred, positive=positive)
    r = rates(cm)
    agree_n = sum(t == p for t, p in zip(truth, pred))
    kappa = agreement_kappa(truth, pred)
    return {
        "n": n,
        "tp": cm["tp"], "fn": cm["fn"], "fp": cm["fp"], "tn": cm["tn"],
        "abstain_pos": cm["abstain_pos"], "abstain_neg": cm["abstain_neg"],
        "agreement": agree_n / n if n else float("nan"),
        "agree_n": agree_n,
        "kappa": kappa,
        "tpr": r["tpr"], "tpr_ci": r["tpr_ci"],
        "tnr": r["tnr"], "tnr_ci": r["tnr_ci"],
        "precision": r["precision"],
        "P": r["P"], "N": r["N"],
        "gold_fail": r["P"],
        "judge_fail": cm["tp"] + cm["fp"],
    }


def track_split(rows, positive="fail"):
    """Split rows with a ``track`` key of ``frozen`` or ``fresh``.

    Each row needs ``truth`` and ``pred``. Returns reports for frozen,
    fresh and the pooled draw, plus the kappa gap (frozen minus fresh).
    """
    frozen = [r for r in rows if r["track"] == "frozen"]
    fresh = [r for r in rows if r["track"] == "fresh"]
    other = [r for r in rows if r["track"] not in ("frozen", "fresh")]
    if other:
        raise ValueError(f"unknown track values: {sorted({r['track'] for r in other})}")
    fr = week_report([r["truth"] for r in frozen], [r["pred"] for r in frozen], positive)
    fs = week_report([r["truth"] for r in fresh], [r["pred"] for r in fresh], positive)
    pooled = week_report(
        [r["truth"] for r in rows], [r["pred"] for r in rows], positive)
    gap = (fr["kappa"] - fs["kappa"]) if (_finite(fr["kappa"]) and _finite(fs["kappa"])) else float("nan")
    return {"frozen": fr, "fresh": fs, "pooled": pooled, "gap": gap}


def rolling_median(values):
    """Median of a list of numbers, ignoring NaN. Empty -> NaN."""
    xs = sorted(v for v in values if _finite(v))
    if not xs:
        return float("nan")
    m = len(xs) // 2
    if len(xs) % 2:
        return xs[m]
    return 0.5 * (xs[m - 1] + xs[m])


def _grade_kappa(kappa, drop, thr=None):
    thr = thr or THRESHOLDS
    if not _finite(kappa):
        return "unparsed"
    fail = (kappa < thr["kappa_floor_fail"]) or (
        _finite(drop) and drop >= thr["drop_fail"])
    flag = (kappa < thr["kappa_floor_flag"]) or (
        _finite(drop) and drop >= thr["drop_flag"])
    if fail:
        return "fail"
    if flag:
        return "flag"
    return "pass"


def diagnose(frozen_drop, fresh_drop, gap, thr=None):
    """Say whether the judge moved, the world moved, both, or neither.

    A track 'moved' when its drop reaches the flag cut-off. A large
    gap between tracks is supporting evidence, not a third cause.
    """
    thr = thr or THRESHOLDS
    frozen_moved = _finite(frozen_drop) and frozen_drop >= thr["drop_flag"]
    fresh_moved = _finite(fresh_drop) and fresh_drop >= thr["drop_flag"]
    if frozen_moved and fresh_moved:
        return "both"
    if (not frozen_moved) and fresh_moved:
        return "world_moved"
    if frozen_moved and (not fresh_moved):
        return "judge_moved"
    return "none"


def alert(history, this_week, thr=None):
    """Compare one week's two-track report to the rolling history.

    ``history`` is a list of prior ``track_split`` results (oldest first).
    ``this_week`` is a ``track_split`` result. Returns a verdict of
    pass, flag or fail, the diagnostic, and the drops that produced it.
    """
    thr = dict(THRESHOLDS if thr is None else thr)
    pooled_hist = [h["pooled"]["kappa"] for h in history]
    frozen_hist = [h["frozen"]["kappa"] for h in history]
    fresh_hist = [h["fresh"]["kappa"] for h in history]
    base_p = rolling_median(pooled_hist)
    base_fr = rolling_median(frozen_hist)
    base_fs = rolling_median(fresh_hist)
    k = this_week["pooled"]["kappa"]
    drop = (base_p - k) if (_finite(base_p) and _finite(k)) else float("nan")
    fr_k = this_week["frozen"]["kappa"]
    fs_k = this_week["fresh"]["kappa"]
    frozen_drop = (base_fr - fr_k) if (_finite(base_fr) and _finite(fr_k)) else float("nan")
    fresh_drop = (base_fs - fs_k) if (_finite(base_fs) and _finite(fs_k)) else float("nan")
    gap = this_week.get("gap", (
        fr_k - fs_k if (_finite(fr_k) and _finite(fs_k)) else float("nan")))
    verdict = _grade_kappa(k, drop, thr)
    # A large track gap escalates a pass to a flag, never a fail on its own.
    if verdict == "pass" and _finite(gap) and abs(gap) >= thr["track_gap_flag"]:
        verdict = "flag"
    reason = diagnose(frozen_drop, fresh_drop, gap, thr)
    return {
        "verdict": verdict,
        "diagnostic": reason,
        "kappa": k,
        "baseline": base_p,
        "drop": drop,
        "frozen_kappa": fr_k,
        "fresh_kappa": fs_k,
        "frozen_drop": frozen_drop,
        "fresh_drop": fresh_drop,
        "gap": gap,
        "n_history": len(history),
    }


def slice_disagreements(rows, key="slice"):
    """Count agreements and disagreements by an arbitrary slice key."""
    out = {}
    for r in rows:
        k = r[key]
        rec = out.setdefault(k, {"n": 0, "agree": 0, "disagree": 0})
        rec["n"] += 1
        if r["truth"] == r["pred"]:
            rec["agree"] += 1
        else:
            rec["disagree"] += 1
    for rec in out.values():
        rec["disagree_rate"] = rec["disagree"] / rec["n"] if rec["n"] else float("nan")
    return out


def version_record(name, prompt, model_pin, rubric, policy_doc, card, role,
                   admitted_on=""):
    """Pin the artefacts that make a judge a specific instrument.

    The digest is the first twelve hex characters of the SHA-256 of a
    canonical JSON object. Changing any pinned field changes the digest.
    ``admitted_on`` is recorded but not hashed, so a later signature on
    the same content does not mint a new version.
    """
    pinned = {
        "name": name,
        "prompt": prompt,
        "model_pin": model_pin,
        "rubric": rubric,
        "policy_doc": policy_doc,
        "card": card,
        "role": role,
    }
    blob = json.dumps(pinned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()[:12]
    return {
        **pinned,
        "admitted_on": admitted_on,
        "digest": digest,
    }


def same_version(a, b):
    """True when two version records share a digest."""
    return a["digest"] == b["digest"]


def change_control(old_checks, new_checks, *, frozen_ids, allowed_rewrites=None):
    """Hold a revision that deletes or silently rewrites a frozen check.

    ``old_checks`` and ``new_checks`` are lists of dicts with ``id`` and
    ``text``. ``frozen_ids`` are the checks that came from gold labels or
    from the metric card; they may be rewritten only when
    ``allowed_rewrites`` maps the check id to a policy ruling id.
    Additions are always allowed. A hold lists what it blocked.
    """
    allowed_rewrites = allowed_rewrites or {}
    old = {c["id"]: c for c in old_checks}
    new = {c["id"]: c for c in new_checks}
    if len(old) != len(old_checks) or len(new) != len(new_checks):
        raise ValueError("check ids must be unique inside each revision")
    deleted = sorted(i for i in old if i not in new)
    added = sorted(i for i in new if i not in old)
    rewritten = sorted(
        i for i in old if i in new and old[i].get("text") != new[i].get("text"))
    deleted_frozen = [i for i in deleted if i in frozen_ids]
    rewritten_unapproved = [
        i for i in rewritten if i in frozen_ids and i not in allowed_rewrites]
    rewritten_approved = [
        i for i in rewritten if i in frozen_ids and i in allowed_rewrites]
    rewritten_free = [i for i in rewritten if i not in frozen_ids]
    if deleted_frozen or rewritten_unapproved:
        verdict = "hold"
    else:
        verdict = "pass"
    return {
        "verdict": verdict,
        "deleted": deleted,
        "added": added,
        "rewritten": rewritten,
        "deleted_frozen": deleted_frozen,
        "rewritten_unapproved": rewritten_unapproved,
        "rewritten_approved": rewritten_approved,
        "rewritten_free": rewritten_free,
        "rulings": {i: allowed_rewrites[i] for i in rewritten_approved},
    }


def revalidate(report, *, tpr_floor=0.80, tnr_floor=0.90, kappa_floor=0.75):
    """Admit or refuse a judge version on a freshly labelled set.

    Floors on TPR and TNR are applied to the Wilson lower bound, matching
    Chapter 16's admission rule. The kappa floor is applied to the point
    estimate; Chapter 18's report card is the fuller packet this check
    does not replace.
    """
    tpr_lo = report["tpr_ci"][0] if report.get("tpr_ci") else float("nan")
    tnr_lo = report["tnr_ci"][0] if report.get("tnr_ci") else float("nan")
    reasons = []
    if not _finite(tpr_lo) or tpr_lo < tpr_floor:
        reasons.append("tpr_bound")
    if not _finite(tnr_lo) or tnr_lo < tnr_floor:
        reasons.append("tnr_bound")
    if not _finite(report.get("kappa", float("nan"))) or report["kappa"] < kappa_floor:
        reasons.append("kappa")
    return {
        "verdict": "admit" if not reasons else "refuse",
        "reasons": reasons,
        "tpr": report.get("tpr"),
        "tpr_lo": tpr_lo,
        "tnr": report.get("tnr"),
        "tnr_lo": tnr_lo,
        "kappa": report.get("kappa"),
        "n": report.get("n"),
    }


# Re-export so callers that only import drift can still name the pieces.
wilson = wilson
cohen_kappa = _kappa
