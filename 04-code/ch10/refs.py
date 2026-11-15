"""Chapter 10 reference sets. Both are planted fixture text.

CURRENT  written by Grace Holloway and Ben Fletcher in May 2027 from fee-schedule-2026-03: one
         reference per right answer, filled with the trace's facts.
STALE    the answer key Ryan assembled during the build from the help-centre FAQ export, which
         still carried fee-schedule-2024-01's text (ten-day grace; waivers by phone). It has no
         entry for a fee-tool failure, so those traces fall back to its "stands" entry.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.reference import RefSet  # noqa: E402
import fee200 as F  # noqa: E402

CURRENT = RefSet("fee-refs-2027-05", "Grace Holloway and Ben Fletcher", "2027-05-04", "fee-schedule-2026-03", {
    "stands": "The $25 late fee on your loan ending {asked} stands. Your payment posted {days} days after the due date, "
              "and the grace period is 15 days. Setting up autopay or paying a few days early will avoid the fee next time.",
    "waive": "Your loan ending {asked} qualifies for a courtesy waiver, because autopay borrowers receive one every "
             "twelve months. The $25 late fee will be reversed and you do not need to pay it.",
    "officer": "A waiver request is already open on your loan ending {asked}. A loan officer will confirm within two "
               "business days whether the $25 late fee is removed.",
    "officer_tool": "I could not load the fee details for your loan ending {asked} just now. A loan officer will review "
                    "the late fee and confirm within two business days.",
})

STALE = RefSet("compass-answer-key", "Ryan Mitchell", "build phase", "fee-schedule-2024-01", {
    "stands": "Late fees are charged when a payment arrives more than ten days after the due date. Your payment was "
              "{days} days late, so the $25 late fee applies to your loan ending {asked}.",
    "waive": "Late fees can be waived at our discretion. Please call us to request a waiver of the $25 late fee on "
             "your loan ending {asked}.",
    "officer": "Late fees can be waived at our discretion. Please call us to request a waiver of the $25 late fee on "
               "your loan ending {asked}.",
})


def ref_for(t, refset=CURRENT):
    sit = F.RIGHT[t["kind"]]
    if sit not in refset.texts:
        sit = "stands"
    return refset.text(sit, asked=t["asked"], days=t["days"])
