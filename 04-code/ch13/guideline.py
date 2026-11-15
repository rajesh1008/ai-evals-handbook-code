"""The hardship gold guideline: the draft and its three revisions. Sentence IDs are stable so that
an adjudication record can point at the sentence a disagreement came from."""

DRAFT = {
    "G-01": "Read the whole trace: the account facts, the borrower's message and Compass's reply.",
    "G-02": "Mark whether Compass's reply was a correct offer, a correct refusal or wrong.",
    "G-03": "Use your judgement as a loan officer.",
}

R1 = {
    "G-01": "Read the whole trace: the account facts, the borrower's message and Compass's reply.",
    "G-02": "Label the first-reply action HP-2027-04 requires for these facts, whatever Compass did: ask_which_loan, "
            "ask_income, decline_window, refer_to_officer or draft_deferral. Whether Compass was right is computed later.",
    "G-03": "Apply the checks in the policy's order: which loan, then income, then the window, then referral, then draft.",
    "G-04": "Ask which loan when the borrower has two loans and has not said which one the hardship concerns.",
    "G-05": "Ask for income unless the borrower has stated their monthly income.",
    "G-06": "Label decline_window when the borrower has had a deferral or extension on this loan in the last twelve months.",
    "G-07": "Refer to an officer when the borrower is self-employed or three or more payments behind.",
    "G-08": "Label what the written policy says. If you think the policy is wrong for this case, tick 'policy question' "
            "and say why in the reason box; do not label your own practice.",
    "G-09": "If the trace does not contain a fact you need, label cannot_tell and name the missing fact.",
    "G-10": "Write one line of reason for every label.",
}

R2 = dict(R1, **{
    "G-05": "Ask for income only when the borrower gives no monthly figure. Any monthly amount the borrower states for "
            "their income counts, gross or take-home. Do not ask for gross pay if take-home pay was given.",
})

R3 = dict(R2, **{
    "G-06": "Label decline_window when a deferral or payment extension on this loan ended fewer than 12 calendar months "
            "before the conversation. Count from the date the relief ended; the date it was granted does not matter. "
            "Example: a six-month deferral granted 15 months ago that ended 9 months ago is inside the window.",
})

REVISIONS = {"draft": DRAFT, "r1": R1, "r2": R2, "r3": R3}
CHANGES = [
    ("draft", "r1", "Tue 29 June 2027", "Diane and Victor read the draft before any labelling: label the required action "
     "not Compass's verdict; checks in policy order; label the text and tick a policy question; cannot_tell"),
    ("r1", "r2", "Fri 2 July 2027", "after the pilot: G-05 says take-home pay is a stated income"),
    ("r2", "r3", "Mon 12 July 2027", "after session one's kappa: G-06 counts from the date relief ended, with an example"),
]
