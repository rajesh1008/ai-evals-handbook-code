"""Chapter 12: the hardship rules Compass applies in its first reply, as code.

This is the book's summary of HP-2027-04 (reissued Thu 1 April 2027), reduced to the five first-reply
actions the lab scores. It is the ground truth for every synthetic case: the generator's own label is
recorded and compared, but never used.
"""
POLICY_TEXT = """Harbor Lending hardship policy HP-2027-04 (summary used by Compass for the first reply).
4.1 A borrower facing a hardship may be offered a deferral, drafted by Compass and approved by a loan officer.
4.2 Income and expenses: Compass must have the borrower's current monthly income before drafting anything.
    If the borrower has not stated a monthly income, the first reply asks for it (action: ask_income).
4.3 Window: a borrower who has had a deferral or a payment extension on the same loan that ended fewer than
    12 calendar months ago is not eligible; Compass explains this and offers a call with an officer
    (action: decline_window). Relief that ended 12 or more calendar months ago does not count.
4.4 Every offer is approved by a loan officer before it takes effect.
4.5 Self-employed borrowers, and borrowers three or more payments behind, are referred to a loan officer
    instead of receiving a drafted offer (action: refer_to_officer).
4.6 A borrower with more than one loan who has not said which loan the hardship concerns is asked which
    loan first (action: ask_which_loan).
Otherwise Compass drafts a deferral for officer approval (action: draft_deferral).
Order of checks: 4.6, then 4.2, then 4.3, then 4.5, then draft."""

ACTIONS = ("ask_which_loan", "ask_income", "decline_window", "refer_to_officer", "draft_deferral")


def decide(case):
    """The first-reply action HP-2027-04 requires for a case's facts."""
    loans = case["loans"]
    if len(loans) > 1 and not case.get("names_loan"):
        return "ask_which_loan"
    if case.get("income_monthly") in (None, 0):
        return "ask_income"
    pr = case.get("prior_relief")
    if pr and pr.get("months_ago") is not None and pr["months_ago"] < 12:
        return "decline_window"
    if case.get("income_type") == "self_employed" or max(l.get("payments_behind", 0) for l in loans) >= 3:
        return "refer_to_officer"
    return "draft_deferral"
