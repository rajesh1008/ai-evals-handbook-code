"""Shared loading for the Chapter 22 analyses (no model calls; reads the cached real runs)."""
import statistics
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss import rationale as RA  # noqa: E402
from truss.checks import within_months  # noqa: E402
from truss.trial import validation_table  # noqa: E402

import fixture as F  # noqa: E402
import judges as J  # noqa: E402
import llm  # noqa: E402

STUDY = F.study_set()
BY_ID = {t["trace_id"]: t for t in STUDY}
DEV = [t for t in STUDY if t["split"] == "dev"]
TEST = [t for t in STUDY if t["split"] == "test"]
MONTHLY_FEE = 3514        # fee conversations a month at the 10% arm (Chapter 16)
READ_MIN, OFFICER_RATE = 3.0, 60.0   # minutes to read a flagged verdict with its trace; $ an hour (Chapter 1)
PRICE_OUT = llm.PRICE[llm.SMALL][1]


def window(t):
    if not t["waiver"]:
        return None
    inside = within_months(date.fromisoformat(t["waiver"]), date.fromisoformat(t["fee_date"]), 12, anniversary_inside=False)
    return "inside" if inside else "outside"


def status(t):
    if t["kind"] == "defer_open":
        return "defer"
    if t["hb"]:
        return "waived"
    if not t["autopay"]:
        return "stands"
    return "stands" if window(t) == "inside" else "waived"


def trace_dates(t):
    return RA.extract_dates(F.account_span(t)) | {t["fee_date"], t["due"]}


def rows(run="v2", reader=None, claims=None):
    """One row per trace for a judge run: verdict, error, style features, consistency, claim check."""
    R = J.load(run)
    RD = J.load(reader or f"read_{run}") if (reader or f"read_{run}") in J.ORDER else {}
    CL = J.load(claims or f"claims_{run}") if (claims or f"claims_{run}") in J.ORDER else {}
    out = []
    for i in sorted(R):
        t = BY_ID[i]
        txt = J.strip_verdict(R[i]["text"])
        v = J.verdict(R[i]["text"])
        sf = RA.style_features(txt)
        rd = J.reader_json(RD[i]["text"]) if i in RD else {}
        cl = J.reader_json(CL[i]["text"]) if i in CL else {}
        rec = {"fee_date": t["fee_date"], "waiver_date": t["waiver"] if t["kind"] != "X_wrongloan" else None, "window": window(t)}
        cc = RA.claim_check(cl, rec) if cl else {"checked": [], "wrong": []}
        cons = RA.consistency(rd.get("implied_verdict"), v) if rd else "unclear"
        conv = rd.get("convincing") if isinstance(rd.get("convincing"), (int, float)) else None
        out.append({"id": i, "kind": t["kind"], "split": t["split"], "stratum": t["stratum"], "edge": t["edge"],
                    "truth": t["truth"], "verdict": v, "err": int(v != t["truth"]), "text": txt,
                    "words": sf["words"], "hedges": sf["hedges"], "self_correction": sf["self_correction"],
                    "bad_date": bool(RA.dates_not_in_trace(txt, trace_dates(t), allowed={RA.cutoff(t["fee_date"])})),
                    "consistency": cons, "convincing": conv,
                    "claims_checked": cc["checked"], "claims_wrong": cc["wrong"],
                    "status_claim": cl.get("correct_status"), "status_wrong": cl.get("correct_status") in ("stands", "waived", "defer") and cl.get("correct_status") != status(t),
                    "tokens_out": R[i]["out"], "latency": R[i]["latency"]})
    return out


def add_flags(rs, long_words):
    for r in rs:
        r["f_long"] = r["words"] > long_words
        r["f_hedge"] = r["hedges"] >= 1
        r["f_self"] = r["self_correction"]
        r["f_low_conv"] = (r["convincing"] or 5) <= 3
        r["f_contra"] = r["consistency"] != "consistent"
        r["f_bad_date"] = r["bad_date"]
        r["f_window"] = "window" in r["claims_wrong"]
        r["f_cutoff"] = "cutoff" in r["claims_wrong"]
        r["f_wdate"] = "waiver_date" in r["claims_wrong"]
        r["f_status"] = bool(r["status_wrong"])
    return rs


FAMILIES = {"style": ["f_long", "f_hedge", "f_self", "f_low_conv"],
            "consistency": ["f_contra", "f_self"],
            "claim check": ["f_window", "f_cutoff", "f_wdate", "f_bad_date"]}


def table(truth, pred, kinds):
    return validation_table(list(truth), list(pred), list(kinds))


def median(xs):
    return statistics.median(xs)


def pct(x):
    return f"{100 * x:.1f}%"


def ci(c):
    return f"{c[0]:.3f} to {c[1]:.3f}"
