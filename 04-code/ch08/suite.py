"""Chapter 8: the metric suite. One card per active v0.3 failure mode, Victor's two outcome
metrics, four inform-tier signals, and the proposals the registry refused."""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
from truss.metrics import Card, Registry  # noqa: E402

CH7 = HERE.parents[0] / "ch07" / "out"
TAX = json.load(open(CH7 / "taxonomy-v0.3.json"))
CODE = {"F_waive": "FM-06", "X_wrongloan": "FM-22", "P_perdiem": "FM-19", "P_goodthru": "FM-19",
        "X_invent": "FM-24", "L_early": "FM-11", "L_state": "FM-12", "L_address": "FM-23",
        "H_income": "FM-01", "H_refused": "FM-20", "H_ignored": "FM-14", "H_approval": "FM-03",
        "A_date": "FM-07", "A_second": "FM-08", "S_month": "FM-17", "S_yearend": "FM-18"}
# trace evidence named in earlier chapters (Ch6 and Ch7 readings); anything else comes from the
# February frame's first planted case, which the Chapter 7 census or weekly draws read
NAMED = {"FM-06": ["t-086089"], "FM-22": ["t-089334", "t-089546", "t-088267"], "FM-24": ["t-089795", "t-085991"],
         "FM-23": ["t-087375"], "FM-20": ["t-087723"], "FM-14": ["t-088791", "t-019442"],
         "FM-04": ["t-089546"], "FM-21": ["t-072609"], "FM-16": ["t-020266"], "FM-15": ["t-021059"]}


def evidence(feb_frame):
    ev = {k: list(v) for k, v in NAMED.items()}
    for r in feb_frame:
        code = CODE.get(r["cause"])
        if code and code not in NAMED and len(ev.setdefault(code, [])) < 2:
            ev[code].append(r["trace_id"])
    return ev


HARD = "hardship conversations in the replay set or the weekly draw; abandoned excluded and counted"
G = "Grace Holloway (loan officers)"
R = "Ryan Mitchell (engineering)"
E = "evaluation lead"
READ = "loan officer reads every hardship gate case (Chapter 2 rule)"


def cards():
    """(card, note) in registry order. kind = the cheapest instrument that can answer the question;
    instrument = what answers it today."""
    out = [
        Card("MC-01", "wrong hardship offer rate", ("FM-04", "FM-22"),
             "Did Compass draft a hardship offer that policy does not allow on the loan it was drafted for?",
             "hardship conversations with an offer drafted", "code", "gate", G, ("hardship",),
             instrument="offer span joined to the servicing core's deferral history; officer confirms",
             validated="census check agreed with officer reading on every flagged February case (Chapter 7)",
             target=0.005, rule="no_new_fail"),
        Card("MC-02", "wrong fee explanation rate", ("FM-06", "FM-22", "FM-24"),
             "Did the reply state a fee amount, grace period or waiver status that differs from what the fee tool "
             "returned, or would have returned, for the loan the borrower named?",
             "fee conversations, abandoned excluded and counted", "judge", "gate", E, ("fee_explanation",),
             instrument="human reading against the fee tool span (judge from Chapter 16)",
             validated="two readers, binary, March fee draw (this chapter)", deferred_as="fail", target=0.02,
             rule="no_new_fail", weakness="a reply that never states a fee cannot fail it; read beside the deferral rate"),
    ]
    spec = {  # code: (kind, tier, alert, instrument)
        "FM-01": ("judge", "gate", None, READ), "FM-03": ("code", "gate", None, READ + "; check in Chapter 9"),
        "FM-04": ("code", "gate", None, "deferral-history check; " + READ),
        "FM-06": ("judge", "monitor", .05, "human reading of the fee tool span and reply"),
        "FM-07": ("reference", "monitor", .08, "balance as-of date compared with the tool's date"),
        "FM-08": ("judge", "monitor", .06, "human reading; account list from the servicing core"),
        "FM-11": ("reference", "monitor", .09, "promised date compared with the title office date"),
        "FM-12": ("reference", "monitor", .05, "title state compared with the lien record"),
        "FM-14": ("judge", "gate", None, READ), "FM-15": ("code", "gate", None, "queue hours vs callback offer; " + READ),
        "FM-16": ("code", "gate", None, "language tag on the hand-off request; " + READ),
        "FM-17": ("reference", "monitor", .04, "statement month compared with the month asked for"),
        "FM-18": ("code", "monitor", .07, "document type sent vs type asked for"),
        "FM-19": ("reference", "monitor", .08, "quoted per diem and date vs payoff tool; gate once Chapter 9's check validates"),
        "FM-20": ("code", "gate", None, "extension counted as deferral; " + READ + "; check in Chapter 9"),
        "FM-21": ("judge", "gate", None, READ),
        "FM-22": ("code", "gate", None, "wrong-loan census check (Chapter 7) over every conversation"),
        "FM-23": ("reference", "monitor", .05, "letter address vs address change stated in the conversation"),
        "FM-24": ("code", "gate", None, "tool-error census check (Chapter 7) over every conversation"),
    }
    weak = {  # known weaknesses quoted in the chapter
        "FM-21": "a death described indirectly ('since we lost him') is missed by any keyword search; look-alikes by reading",
        "FM-22": "misses a wrong loan when the borrower names the loan by nickname instead of digits (seen once, Chapter 7)",
        "FM-23": "an address change given in an earlier conversation or by phone is invisible to it",
    }
    modes = {m["code"]: m for m in TAX["modes"]}
    for i, (code, (kind, tier, alert, inst)) in enumerate(sorted(spec.items()), 3):
        m = modes[code]
        out.append(Card(f"MC-{i:02d}", m["name"] + " rate", (code,), m["test"],
                        f"{', '.join(m['flows']).replace('_', ' ')} conversations", kind, tier, m["owner"], tuple(m["flows"]),
                        instrument=inst, validated="" if tier != "gate" else "hardship gate reading or census check",
                        alert=alert, rule="no_new_fail" if tier == "gate" else "", weakness=weak.get(code, "")))
    signals = [
        Card("S-01", "CSAT (mean of 1 to 5 survey)", (), "", "surveyed conversations", "signal", "inform", "Rachel Foster"),
        Card("S-02", "self-serve rate", (), "", "all conversations", "signal", "inform", "Rachel Foster"),
        Card("S-03", "reply length in words", (), "", "all replies", "signal", "inform", R),
        Card("S-04", "tool-error rate", (), "", "all conversations", "signal", "inform", R),
    ]
    proposals = [
        Card("P-01", "answer completeness (vendor dashboard, 0 to 1)", (), "Does the reply cover the fee schedule?",
             "fee replies", "judge", "monitor", "vendor"),
        Card("P-02", "helpfulness (1 to 5)", (), "How helpful was the reply?", "all replies", "judge", "monitor", R),
        Card("P-03", "toxicity score", (), "Is the reply toxic?", "all replies", "judge", "gate", "vendor", rule="no_new_fail"),
        Card("P-04", "stale grace period quoted", ("FM-05",), "Did the reply quote a ten-day grace period?",
             "fee replies", "code", "gate", E, validated="index check", rule="no_new_fail"),
        Card("P-05", "wrong-loan payoff rate", ("FM-22",), "Was the payoff quoted for another loan?",
             "payoff conversations", "code", "monitor", R),
    ]
    return out, signals, proposals


def registry(feb_frame):
    status = {m["code"]: m["status"] for m in TAX["modes"]}
    reg = Registry(status, evidence(feb_frame), TAX["digest"])
    cs, sig, props = cards()
    for c in cs + sig:
        reg.add(c)
    for p in props:
        reg.try_add(p)
    return reg


def pilot_fee_ids():
    with open(HERE.parents[0] / "ch02" / "out" / "first_pass_labels.csv") as f:
        return [r["trace_id"] for r in csv.DictReader(f) if r["flow"] == "fee_explanation"]
