"""The hardship annotation guideline for the operation (Chapter 14). Sentence IDs carry over from the gold
guideline of Chapter 13 (revision 3) so that a ruling can point at a sentence. ops-1.0 is revision 3 plus
bulletin HB-2027-07 and two worked examples from the adjudication log; ops-1.1 adds the two sentences the
first alignment session found missing. `INJECTED` is ops-1.1 with the anniversary sentence removed: the
lab's failure injection."""

OPS_10 = {
    "G-01": "Read the account facts and the borrower's message. Compass's reply is hidden until you have saved your label.",
    "G-02": "Label the first-reply action HP-2027-04 requires for these facts: ask_which_loan, ask_income, "
            "decline_window, refer_to_officer or draft_deferral.",
    "G-03": "Apply the checks in the policy's order: which loan, then income, then the window, then referral, then draft.",
    "G-04": "Ask which loan when the borrower has two loans and has not said which one. A reference that fits both "
            "loans (\"the car loan\" when both are auto loans) has not said which one.",
    "G-05": "Ask for income only when the borrower gives no monthly figure. Any monthly amount the borrower states "
            "for their income counts, gross or take-home.",
    "G-06": "Label decline_window when a deferral or payment extension on this loan ended fewer than 12 calendar "
            "months before the conversation. Count from the date the relief ended. A disaster forbearance does not "
            "count (bulletin HB-2027-07).",
    "G-07": "Refer to an officer when the borrower is self-employed or three or more payments behind.",
    "G-08": "Label what the written policy says. If you think the policy is wrong for this case, tick 'policy "
            "question' and say why.",
    "G-09": "If the trace does not contain a fact you need, label cannot_tell and name the missing fact.",
    "G-10": "Write one line of reason for every label.",
}

OPS_11 = dict(OPS_10, **{
    "G-06": OPS_10["G-06"] + " Relief that ended exactly 12 calendar months before the conversation is outside "
            "the window: relief that ended on 12 August 2026 does not count in a conversation on 12 August 2027.",
    "G-07": "Refer to an officer when the borrower is self-employed or three or more payments behind. The borrower's "
            "own statement of their current work decides self-employment; the employment on file records what was "
            "true at origination.",
})

INJECTED = dict(OPS_11, **{"G-06": OPS_10["G-06"]})

VERSIONS = {"ops-1.0": OPS_10, "ops-1.1": OPS_11, "ops-1.1-minus-anniversary": INJECTED}
CHANGES = [("ops-1.0", "Mon 9 Aug 2027", "revision 3 of the gold guideline, bulletin HB-2027-07, two worked examples"),
           ("ops-1.1", "Mon 16 Aug 2027", "G-06 anniversary example; G-07 stated work decides (alignment session Fri 13 Aug)")]


def has(version, what):
    g = VERSIONS[version]
    return {"anniversary": "exactly 12 calendar months" in g["G-06"],
            "stated_work": "own statement" in g["G-07"],
            "unclear_loan": "fits both" in g["G-04"]}[what]


def text(version):
    return "\n".join(f"{k} {v}" for k, v in VERSIONS[version].items())
