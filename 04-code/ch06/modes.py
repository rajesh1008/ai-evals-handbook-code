"""Chapter 6: the Compass failure taxonomy, v0.1 as it left error analysis, the v0.1.1 patch
that adds inclusion tests, and the v0.2 change set. Every inclusion test is a yes/no question
a reader answers from the trace; `FITS` says which planted causes in the fixture answer yes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.taxonomy import Mode, Taxonomy

H, F, A, P, L, S = ("hardship", "fee_explanation", "account_question", "payoff_letter",
                    "lien_release", "statement_request")
GRACE, LEAD, RYAN = "Grace Holloway (loan officers)", "evaluation lead", "Ryan Mitchell (engineering)"


def v01():
    m = [
        Mode("FM-01", "offer drafted before income confirmed", (H,), "Compass drafts a hardship offer before the borrower has confirmed current income.", layer=3, owner=GRACE, severity="critical"),
        Mode("FM-02", "no hand-off when borrower asked for a person", (H,), "The borrower asked for a person and no loan officer took over.", layer=3, owner=GRACE, severity="high"),
        Mode("FM-03", "offer sent without saying a loan officer must approve it", (H,), "A hardship offer reaches the borrower without the sentence that a loan officer must approve it.", layer=1, owner=GRACE, severity="critical"),
        Mode("FM-04", "second deferral within 12 months offered", (H,), "Compass offers a deferral to a borrower who had one in the last twelve months.", layer=1, owner=GRACE, severity="critical"),
        Mode("FM-05", "ten-day grace period quoted (policy is 15)", (F,), "Compass quotes the retired ten-day grace period; policy is fifteen days.", layer=1, owner=LEAD, severity="high"),
        Mode("FM-06", "fee not waived when policy says waive", (F,), "Compass explains a late fee that policy says should be waived.", layer=3, owner=LEAD, severity="high"),
        Mode("FM-07", "wrong balance date", (A,), "The balance Compass quotes is dated wrongly.", layer=2, owner=LEAD),
        Mode("FM-08", "missed borrower's second loan", (A,), "Compass answers about one loan when the borrower has two.", layer=3, owner=LEAD),
        Mode("FM-09", "per diem interest omitted", (P,), "The payoff quote leaves out daily interest.", layer=1, owner=LEAD, severity="high"),
        Mode("FM-10", "wrong good-through date", (P,), "The payoff quote's good-through date is wrong.", layer=1, owner=LEAD, severity="high"),
        Mode("FM-11", "release promised before title office date", (L,), "Compass promises the lien release sooner than the title office can record it.", layer=3, owner=LEAD),
        Mode("FM-12", "wrong title state", (L,), "The release goes to, or names, the wrong state's title office.", layer=2, owner=LEAD),
        Mode("FM-13", "wrong statement period", (S,), "The statement sent covers a different period from the one asked for.", layer=2, owner=LEAD, severity="high"),
    ]
    t = Taxonomy("0.1")
    for x in m:
        t.modes[x.code] = x
    return t


TESTS_011 = {
    "FM-01": "Did a hardship offer appear before the borrower confirmed income in this conversation?",
    "FM-02": "Did the borrower ask for a person, and did the conversation end without a loan officer taking over?",
    "FM-03": "Does a reply containing an offer lack the sentence that a loan officer must approve it?",
    "FM-04": "Did Compass offer a deferral when the eligibility tool showed a deferral in the last twelve months?",
    "FM-05": "Does a reply state a ten-day grace period?",
    "FM-06": "Did the fee tool return waive=true while the reply defends the fee?",
    "FM-07": "Does the balance date in the reply differ from the as-of date the balance tool returned?",
    "FM-08": "Did the loan tool return two or more loans while the reply addresses one without saying so?",
    "FM-09": "Does the payoff amount in the reply lack the per diem the payoff tool returned?",
    "FM-10": "Does the good-through date in the reply differ from the one the payoff tool returned?",
    "FM-11": "Does the reply promise a release date earlier than the title office date the lien tool returned?",
    "FM-12": "Does the release name a title state different from the one on the loan record?",
    "FM-13": "Did the borrower ask for a monthly statement for one month and receive the monthly statement for another?",
}

# which planted causes answer each inclusion test "yes"
FITS = {
    "FM-01": {"H_income"}, "FM-02": {"H_ignored", "H_closed", "H_spanish"}, "FM-03": {"H_approval"},
    "FM-04": {"H_second"}, "FM-05": {"F_tenday"}, "FM-06": {"F_waive"}, "FM-07": {"A_date"},
    "FM-08": {"A_second"}, "FM-09": {"P_perdiem"}, "FM-10": {"P_goodthru"}, "FM-11": {"L_early"},
    "FM-12": {"L_state"}, "FM-13": {"S_month"},
    # v0.2
    "FM-14": {"H_ignored"}, "FM-15": {"H_closed"}, "FM-16": {"H_spanish"}, "FM-17": {"S_month"},
    "FM-18": {"S_yearend"}, "FM-19": {"P_perdiem", "P_goodthru"}, "FM-20": {"H_refused"},
    "FM-21": {"H_bereave"},
}


def patch_011(t):
    for code, q in TESTS_011.items():
        t.reword(code, "inclusion test written", test=q)
    return t.release("patch")


def v02_changes(t):
    """The January change set, in the order the chapter discusses it."""
    t.split("FM-02", [
        Mode("FM-14", "request for a person not acted on", (H,), "The borrower asked for a person during staffed hours and Compass carried on.",
             test="Did the borrower ask for a person while the hand-off queue was open, with no hand-off attempted?", layer=3, owner=GRACE, severity="high", added_in="0.2"),
        Mode("FM-15", "out-of-hours hand-off with no callback offered", (H,), "The hand-off tool returned queue closed and the reply offered no callback.",
             test="Did the hand-off tool return closed while the reply offered no callback time?", layer=1, owner=RYAN, severity="high", added_in="0.2"),
        Mode("FM-16", "request for a person in Spanish not recognised", (H,), "The borrower asked for a person in Spanish and the router kept the hardship flow.",
             test="Was the request for a person written in Spanish, with no hand-off intent logged by the router?", layer=2, owner=RYAN, severity="high", added_in="0.2"),
    ], "one code, three causes with three owners; note clusters 3")
    t.split("FM-13", [
        Mode("FM-17", "statement for the wrong month", (S,), "A monthly statement for a month other than the one asked for.",
             test=TESTS_011["FM-13"], layer=2, owner=LEAD, severity="high", added_in="0.2"),
        Mode("FM-18", "year-end interest statement asked for, monthly statement sent", (S,), "The borrower asked for the year-end interest statement and got a monthly one.",
             test="Did the borrower ask for a year-end or tax statement and receive a monthly statement?", excludes="A monthly statement for the wrong month is FM-17.",
             layer=1, owner=RYAN, severity="high", added_in="0.2"),
    ], "fit test failed on most FM-13 labels in January; the statement tool has no year-end type")
    t.merge(["FM-09", "FM-10"], Mode("FM-19", "payoff quote's per diem or good-through date wrong or missing", (P,),
            "The payoff quote disagrees with the payoff tool on per diem or good-through date.",
            test="Does the payoff quote in the reply differ from the payoff tool on per diem interest or good-through date?",
            layer=1, owner=RYAN, severity="high", added_in="0.2", facets=("per diem", "good-through")),
            "same tool field comparison, same owner, coders confuse the two, no one reports them apart")
    t.add(Mode("FM-20", "eligible borrower refused: payment extension counted as a deferral", (H,),
               "Compass refuses a deferral by counting a payment extension older than twelve months as a prior deferral.",
               test="Did the reply refuse a deferral, citing a payment extension that ended more than twelve months before the conversation?",
               excludes="Offering to an ineligible borrower is FM-04.", layer=1, owner=GRACE, severity="critical", added_in="0.2"),
          "open codes in January re-code; no v0.1 mode covers a wrong refusal")
    t.add(Mode("FM-21", "bereavement handled as ordinary hardship", (H,),
               "A borrower reports a co-borrower's death and Compass runs the ordinary hardship script.",
               test="Did the borrower say a co-borrower died, with no hand-off to the estate team?",
               layer=3, owner=GRACE, severity="critical", status="provisional", added_in="0.2", source="incident 19 Jan 2027"),
          "complaint 19 Jan 2027; compliance event")
    t.retire("FM-05", "L1 check: no retired document in the policy index (commit, pull request, release)",
             "cause removed 16 Dec 2026; zero occurrences since; the guard blocks the cause")
    return t
