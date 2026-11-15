"""Chapter 19 fixture: six weekly canaries and a 200-trace revalidation set.

Judges and gold are SIMULATED (planted confusion matrices, seed 2026).
Truss computations on the verdicts are real. The matrices are constructed
so that Harbor's published figures (weekly kappa near 0.81, a drop to 0.62,
recovery on a 200-trace revalidation) fall out of the same functions the
chapter calls, not out of a later edit.
"""
from __future__ import annotations

import hashlib
from copy import deepcopy

SEED = 2026

# Forty traces pinned from the Chapter 18 validation gold (October
# fortnight identifiers reserved so Chapter 18 can
# assign t-185251 upward without colliding).
FROZEN_IDS = [f"t-{184901 + i:06d}" for i in range(40)]

# Fresh weekly samples sit inside each production week, well above
# t-185250. Volume assumption (~4,000 conversations a week at 10%
# traffic) is logged in the study register, not generated here.
WEEK_META = [
    # (week_id, start_date, production_week_start_id, policy, judge)
    ("w1", "2027-11-15", 201251, "HP-2027-04", "fee-judge-v1"),
    ("w2", "2027-11-22", 205251, "HP-2027-04", "fee-judge-v1"),
    ("w3", "2027-11-29", 209251, "HP-2027-04", "fee-judge-v1"),
    ("w4", "2027-12-06", 213251, "HB-2027-12", "fee-judge-v1"),  # drop
    ("w5", "2027-12-13", 217251, "HB-2027-12", "fee-judge-v1"),  # still old judge
    ("w6", "2027-12-20", 221251, "HB-2027-12", "fee-judge-v2"),  # recovered
]

# Confusion matrices (tp, fn, fp, tn) for fail-as-positive.
# Frozen under v1 is identical every week the judge is unchanged.
FROZEN_V1 = (7, 1, 1, 31)          # n=40, kappa ~ 0.844
FROZEN_V2 = (8, 1, 1, 30)          # after re-derivation, n=40

FRESH = {
    "w1": (10, 2, 2, 46),          # pooled with frozen-v1 -> 17/3/3/77, kappa 0.8125
    "w2": (11, 2, 3, 44),
    "w3": (10, 1, 2, 47),
    "w4": (15, 5, 9, 31),          # pooled -> 22/6/10/62, kappa 0.62
    "w5": (14, 6, 8, 32),
    "w6": (18, 0, 1, 41),          # pooled with frozen-v2 -> 26/1/2/71
}

# Week-4 fresh slice: all 14 disagreements sit in the 20 plan_fee traces.
# plan_fee 2/5/9/4 (n=20) + other 13/0/0/27 (n=40) = 15/5/9/31.
W4_PLAN_FEE = (2, 5, 9, 4)
W4_OTHER = (13, 0, 0, 27)

# 200-trace revalidation under HB-2027-12 with fee-judge-v2.
REVALIDATION = (46, 4, 6, 144)     # n=200, kappa ~ 0.868, floors clear
REVALIDATION_IDS = [f"t-{218001 + i:06d}" for i in range(200)]


def expand(tp, fn, fp, tn, pos="fail", neg="pass"):
    truth = [pos] * tp + [pos] * fn + [neg] * fp + [neg] * tn
    pred = [pos] * tp + [neg] * fn + [pos] * fp + [neg] * tn
    return truth, pred


def _rows_from_matrix(ids, matrix, track, week, policy, judge, slices=None):
    truth, pred = expand(*matrix)
    assert len(ids) == len(truth), (len(ids), len(truth), matrix)
    rows = []
    for i, (tid, t, p) in enumerate(zip(ids, truth, pred)):
        sl = slices[i] if slices is not None else "other"
        rows.append({
            "trace_id": tid,
            "track": track,
            "week": week,
            "policy": policy,
            "judge": judge,
            "truth": t,
            "pred": p,
            "slice": sl,
        })
    return rows


def _fresh_ids(week_start_id, n=60):
    # Offset 50 keeps the sample away from the week's first production id
    # without claiming these are the only traces that week.
    return [f"t-{week_start_id + 50 + i:06d}" for i in range(n)]


def _w4_fresh_slices():
    # Matches W4_PLAN_FEE then W4_OTHER under expand() order.
    tp, fn, fp, tn = W4_PLAN_FEE
    plan = ["plan_fee"] * (tp + fn + fp + tn)
    tp, fn, fp, tn = W4_OTHER
    other = ["other"] * (tp + fn + fp + tn)
    return plan + other


def frozen_rows(week_id, start, policy, judge):
    matrix = FROZEN_V2 if judge == "fee-judge-v2" else FROZEN_V1
    return _rows_from_matrix(
        FROZEN_IDS, matrix, "frozen", week_id, policy, judge,
        slices=["plan_fee"] * 8 + ["other"] * 32,
    )


def fresh_rows(week_id, start, policy, judge):
    ids = _fresh_ids(start, 60)
    if week_id == "w4":
        plan = _rows_from_matrix(
            ids[:20], W4_PLAN_FEE, "fresh", week_id, policy, judge,
            slices=["plan_fee"] * 20)
        other = _rows_from_matrix(
            ids[20:], W4_OTHER, "fresh", week_id, policy, judge,
            slices=["other"] * 40)
        return plan + other
    sl = (["plan_fee"] * 8 + ["other"] * 52) if week_id != "w6" else (
        ["plan_fee"] * 12 + ["other"] * 48)
    if week_id == "w5":
        # Same concentration pattern, slightly different counts.
        # 14/6/8/32 split as plan_fee 3/6/8/3 (n=20) + other 11/0/0/29 (n=40).
        plan = _rows_from_matrix(
            ids[:20], (3, 6, 8, 3), "fresh", week_id, policy, judge,
            slices=["plan_fee"] * 20)
        other = _rows_from_matrix(
            ids[20:], (11, 0, 0, 29), "fresh", week_id, policy, judge,
            slices=["other"] * 40)
        return plan + other
    return _rows_from_matrix(
        ids, FRESH[week_id], "fresh", week_id, policy, judge, slices=sl)


def weeks():
    """Six weekly canaries of 100 rows (40 frozen + 60 fresh)."""
    out = []
    for week_id, start_date, start_id, policy, judge in WEEK_META:
        rows = frozen_rows(week_id, start_id, policy, judge)
        rows += fresh_rows(week_id, start_id, policy, judge)
        out.append({
            "week": week_id,
            "start": start_date,
            "policy": policy,
            "judge": judge,
            "rows": rows,
        })
    return out


def revalidation_rows():
    slices = ["plan_fee"] * 40 + ["other"] * 160
    return _rows_from_matrix(
        REVALIDATION_IDS, REVALIDATION, "fresh", "revalidation",
        "HB-2027-12", "fee-judge-v2", slices=slices)


OLD_RUBRIC = [
    {"id": "loan", "text": "The reply names the loan on the tool span."},
    {"id": "late_fee", "text": "The stated late-fee amount matches the schedule."},
    {"id": "window", "text": "The waiver window is the one the span reports."},
    {"id": "waive_or_charge",
     "text": "Fees that relate to the payment which triggered an approved "
             "hardship plan remain chargeable unless a loan officer waives them."},
    {"id": "invent", "text": "The reply does not invent a waiver or a charge."},
]

NEW_RUBRIC = deepcopy(OLD_RUBRIC)
for check in NEW_RUBRIC:
    if check["id"] == "waive_or_charge":
        check["text"] = (
            "The late fee and the returned-payment fee on the payment that "
            "triggered an approved hardship plan are waived automatically."
        )

FROZEN_CHECKS = {"loan", "late_fee", "window", "waive_or_charge", "invent"}

PROMPT_V1 = (
    "Critique the fee explanation against the five rules, then give a "
    "binary verdict. Quote the card question verbatim."
)
MODEL_PIN = "small-fast-provider-snapshot-2027-10"


def describe():
    return {
        "seed": SEED,
        "frozen_ids": (FROZEN_IDS[0], FROZEN_IDS[-1]),
        "n_frozen": 40,
        "n_fresh": 60,
        "weeks": [w[0] for w in WEEK_META],
        "policy_change": "HB-2027-12",
        "effective": "2027-12-06",
        "fixture_digest": hashlib.sha256(
            repr((FROZEN_V1, FROZEN_V2, FRESH, REVALIDATION, SEED)).encode()
        ).hexdigest()[:12],
    }
