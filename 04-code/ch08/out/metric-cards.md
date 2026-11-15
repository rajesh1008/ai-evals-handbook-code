# Compass metric cards, Truss v1 (0.11.0), taxonomy v0.3 (961c7955ebfc)

### MC-01 wrong hardship offer rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-04, FM-22 |
| question | Did Compass draft a hardship offer that policy does not allow on the loan it was drafted for? |
| population | hardship conversations with an offer drafted |
| kind | code |
| instrument | offer span joined to the servicing core's deferral history; officer confirms |
| validated | census check agreed with officer reading on every flagged February case (Chapter 7) |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| target | 0.005 |
| owner | Grace Holloway (loan officers) |

### MC-02 wrong fee explanation rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-06, FM-22, FM-24 |
| question | Did the reply state a fee amount, grace period or waiver status that differs from what the fee tool returned, or would have returned, for the loan the borrower named? |
| population | fee conversations, abandoned excluded and counted |
| kind | judge |
| instrument | human reading against the fee tool span (judge from Chapter 16) |
| validated | two readers, binary, March fee draw (this chapter) |
| deferred_as | pass |
| tier | gate |
| rule | no_new_fail |
| target | 0.02 |
| owner | evaluation lead |
| weakness | a reply that never states a fee cannot fail it; read beside the deferral rate |
| last measured | 15 in 200 (7.5%, Wilson 4.6% to 12.0%); deferred 23; cannot tell 0 |
| history | 2027-03-19 v1.1: deferral to a loan officer is not a wrong explanation (Victor's ruling, 19 March); deferral rate reported beside the rate, alert at 15% |

### MC-03 offer drafted before income confirmed rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-01 |
| question | Did a hardship offer appear before the borrower confirmed income in this conversation? |
| population | hardship conversations |
| kind | judge |
| instrument | loan officer reads every hardship gate case (Chapter 2 rule) |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Grace Holloway (loan officers) |

### MC-04 offer sent without saying a loan officer must approve it rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-03 |
| question | Does a reply containing an offer lack the sentence that a loan officer must approve it? |
| population | hardship conversations |
| kind | code |
| instrument | loan officer reads every hardship gate case (Chapter 2 rule); check in Chapter 9 |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Grace Holloway (loan officers) |

### MC-05 second deferral within 12 months offered rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-04 |
| question | Did Compass offer a deferral on a loan whose account history shows a deferral in the previous twelve months? |
| population | hardship conversations |
| kind | code |
| instrument | deferral-history check; loan officer reads every hardship gate case (Chapter 2 rule) |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Grace Holloway (loan officers) |

### MC-06 fee not waived when policy says waive rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-06 |
| question | Did the fee tool return waive=true while the reply defends the fee? |
| population | fee explanation conversations |
| kind | judge |
| instrument | human reading of the fee tool span and reply |
| deferred_as | excluded |
| tier | monitor |
| alert | 0.057 |
| owner | evaluation lead |
| history | 2027-03-26 v1.1: alert reset from 5% to 5.7% of a four-week pooled draw of 200 (quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands |

### MC-07 wrong balance date rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-07 |
| question | Does the balance date in the reply differ from the as-of date the balance tool returned? |
| population | account question conversations |
| kind | reference |
| instrument | balance as-of date compared with the tool's date |
| deferred_as | excluded |
| tier | monitor |
| alert | 0.078 |
| owner | evaluation lead |
| history | 2027-03-26 v1.1: alert reset from 8% to 7.8% of a four-week pooled draw of 200 (quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands |

### MC-08 missed borrower's second loan rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-08 |
| question | Did the loan tool return two or more loans, the borrower name none, and the reply address one without saying so? |
| population | account question conversations |
| kind | judge |
| instrument | human reading; account list from the servicing core |
| deferred_as | excluded |
| tier | monitor |
| alert | 0.053 |
| owner | evaluation lead |
| history | 2027-03-26 v1.1: alert reset from 6% to 5.3% of a four-week pooled draw of 200 (quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands |

### MC-09 release promised before title office date rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-11 |
| question | Does the reply promise a release date earlier than the title office date the lien tool returned? |
| population | lien release conversations |
| kind | reference |
| instrument | promised date compared with the title office date |
| deferred_as | excluded |
| tier | monitor |
| alert | 0.082 |
| owner | evaluation lead |
| history | 2027-03-26 v1.1: alert reset from 9% to 8.2% of a four-week pooled draw of 200 (quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands |

### MC-10 wrong title state rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-12 |
| question | Does the release name a title state different from the one on the loan record? |
| population | lien release conversations |
| kind | reference |
| instrument | title state compared with the lien record |
| deferred_as | excluded |
| tier | monitor |
| alert | 0.04 |
| owner | evaluation lead |
| history | 2027-03-26 v1.1: alert reset from 5% to 4.0% of a four-week pooled draw of 200 (quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands |

### MC-11 request for a person not acted on rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-14 |
| question | Did the borrower ask to speak to, or be called by, a person while the hand-off queue was open, with no hand-off attempted? |
| population | hardship conversations |
| kind | judge |
| instrument | loan officer reads every hardship gate case (Chapter 2 rule) |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Grace Holloway (loan officers) |

### MC-12 out-of-hours hand-off with no callback offered rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-15 |
| question | Did the hand-off tool return closed while the reply offered no callback time? |
| population | hardship conversations |
| kind | code |
| instrument | queue hours vs callback offer; loan officer reads every hardship gate case (Chapter 2 rule) |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Ryan Mitchell (engineering) |

### MC-13 request for a person in Spanish not recognised rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-16 |
| question | Was the request for a person written in Spanish, with no hand-off intent logged by the router? |
| population | hardship conversations |
| kind | code |
| instrument | language tag on the hand-off request; loan officer reads every hardship gate case (Chapter 2 rule) |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Ryan Mitchell (engineering) |

### MC-14 statement for the wrong month rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-17 |
| question | Did the borrower ask for a monthly statement for one month and receive the monthly statement for another? |
| population | statement request conversations |
| kind | reference |
| instrument | statement month compared with the month asked for |
| deferred_as | excluded |
| tier | monitor |
| alert | 0.038 |
| owner | evaluation lead |
| history | 2027-03-26 v1.1: alert reset from 4% to 3.8% of a four-week pooled draw of 200 (quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands |

### MC-15 year-end interest statement asked for, monthly statement sent rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-18 |
| question | Did the borrower ask for a year-end or tax statement and receive a monthly statement? |
| population | statement request conversations |
| kind | code |
| instrument | document type sent vs type asked for |
| deferred_as | excluded |
| tier | monitor |
| alert | 0.076 |
| owner | Ryan Mitchell (engineering) |
| history | 2027-03-26 v1.1: alert reset from 7% to 7.6% of a four-week pooled draw of 200 (quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands |

### MC-16 payoff quote's per diem or good-through date wrong or missing rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-19 |
| question | Does the payoff quote in the reply differ from the payoff tool on per diem interest or good-through date? |
| population | payoff letter conversations |
| kind | reference |
| instrument | quoted per diem and date vs payoff tool; gate once Chapter 9's check validates |
| deferred_as | excluded |
| tier | monitor |
| alert | 0.125 |
| owner | Ryan Mitchell (engineering) |
| history | 2027-03-26 v1.1: alert reset from 8% to 12.5% of a four-week pooled draw of 200 (quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands |

### MC-17 eligible borrower refused: payment extension counted as a deferral rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-20 |
| question | Did the reply refuse a deferral, citing a payment extension that ended more than twelve months before the conversation? |
| population | hardship conversations |
| kind | code |
| instrument | extension counted as deferral; loan officer reads every hardship gate case (Chapter 2 rule); check in Chapter 9 |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Grace Holloway (loan officers) |

### MC-18 bereavement handled as ordinary hardship rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-21 |
| question | Did the borrower say a co-borrower died, with no hand-off to the estate team? |
| population | hardship conversations |
| kind | judge |
| instrument | loan officer reads every hardship gate case (Chapter 2 rule) |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Grace Holloway (loan officers) |
| weakness | a death described indirectly ('since we lost him') is missed by any keyword search; look-alikes by reading |

### MC-19 tool called on a loan other than the one the borrower named rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-22 |
| question | Did the borrower name a loan, and does any tool call in the conversation carry a different loan ID? |
| population | fee explanation, payoff letter, hardship, account question conversations |
| kind | code |
| instrument | wrong-loan census check (Chapter 7) over every conversation |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Ryan Mitchell (engineering) |
| weakness | misses a wrong loan when the borrower names the loan by nickname instead of digits (seen once, Chapter 7) |

### MC-20 lien release letter mailed to an address the borrower said had changed rate (card v1.1)

| Field | Value |
|---|---|
| modes | FM-23 |
| question | Did the borrower state a new address, and was the lien letter requested to a different one? |
| population | lien release conversations |
| kind | reference |
| instrument | letter address vs address change stated in the conversation |
| deferred_as | excluded |
| tier | monitor |
| alert | 0.074 |
| owner | Ryan Mitchell (engineering) |
| weakness | an address change given in an earlier conversation or by phone is invisible to it |
| history | 2027-03-26 v1.1: alert reset from 5% to 7.4% of a four-week pooled draw of 200 (quiet-period false alert at most 5%); weekly census alert when Chapter 9's check lands |

### MC-21 answer given as if a failed tool call had returned rate (card v1.0)

| Field | Value |
|---|---|
| modes | FM-24 |
| question | Did a tool span end in error, with a reply that states a figure or action that tool was called for? |
| population | fee explanation, payoff letter, account question, lien release, hardship, statement request conversations |
| kind | code |
| instrument | tool-error census check (Chapter 7) over every conversation |
| validated | hardship gate reading or census check |
| deferred_as | excluded |
| tier | gate |
| rule | no_new_fail |
| owner | Ryan Mitchell (engineering) |

### S-01 CSAT (mean of 1 to 5 survey) (card v1.0)

| Field | Value |
|---|---|
| population | surveyed conversations |
| kind | signal |
| deferred_as | excluded |
| tier | inform |
| owner | Rachel Foster |

### S-02 self-serve rate (card v1.0)

| Field | Value |
|---|---|
| population | all conversations |
| kind | signal |
| deferred_as | excluded |
| tier | inform |
| owner | Rachel Foster |

### S-03 reply length in words (card v1.0)

| Field | Value |
|---|---|
| population | all replies |
| kind | signal |
| deferred_as | excluded |
| tier | inform |
| owner | Ryan Mitchell (engineering) |

### S-04 tool-error rate (card v1.0)

| Field | Value |
|---|---|
| population | all conversations |
| kind | signal |
| deferred_as | excluded |
| tier | inform |
| owner | Ryan Mitchell (engineering) |
