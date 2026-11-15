"""Chapter 7 fixture: Compass traces from Mon 1 to Sun 14 February 2027, the fortnight after
the February release (Ryan's callback template, the bereavement intent, and the new tool-call
wrapper both fixes needed). Seed 2026. Causes are planted; the notebook entries the chapter
prints are in notebook_data.py and are joined to the drawn traces by reading position.

Assumptions carried from the ledger and Chapter 6: about 572 conversations a day; IDs continue
from t-084024; loan-officer queue staffed 08:00 to 19:00 Phoenix time; the extension rule that
causes FM-20 is still in place (Chapter 9 rewrites it). Planted this fortnight:
  X_wrongloan  the wrapper passes the first loan on the account to tools when a borrower with two
               loans names one by its last four digits (FM-22 in v0.3)
  X_invent     a tool error comes back as an empty result and Compass answers as if it had data
               (FM-24 in v0.3)
  L_address    the lien letter is mailed to the address on file after the borrower said it changed
               (open code t-071074 in January; FM-23 in v0.3)
"""
import random
from datetime import date, datetime, timedelta

SEED = 2026
FIRST_ID = 84024
DAYS = [date(2027, 2, 1) + timedelta(d) for d in range(14)]
PER_DAY = 572
SHARES = {"account_question": .39, "fee_explanation": .20, "statement_request": .19,
          "payoff_letter": .10, "lien_release": .06, "hardship": .06}
TIER = {"account_question": "low", "statement_request": "low", "fee_explanation": "medium",
        "payoff_letter": "medium", "lien_release": "medium", "hardship": "high"}
TURNS = {"account_question": 3.6, "fee_explanation": 6.5, "statement_request": 3.6,
         "payoff_letter": 5.5, "lien_release": 7.6, "hardship": 13.5}
GROUP = {"fee_explanation": "fee", "payoff_letter": "payoff and lien", "lien_release": "payoff and lien",
         "hardship": "hardship", "account_question": "account and statement",
         "statement_request": "account and statement"}
LOAN_FLOWS = ("fee_explanation", "payoff_letter", "hardship", "account_question")
TWO_LOANS = .10          # conversations from borrowers with two loans
BY_DIGITS = .30          # of those, the borrower names the loan by its last four digits
TOOL_ERROR = .045        # conversations with at least one tool span in error
INVENT = .16             # of tool-error conversations in payoff, account, fee: Compass answers anyway
ABANDON = .06
CAUSES = {   # per-trace probabilities of the v0.2 causes still live in February
    "hardship": {"H_income": .035, "H_ignored": .03, "H_approval": .015, "H_refused": .055},
    "fee_explanation": {"F_waive": .04},
    "account_question": {"A_date": .045, "A_second": .03},
    "payoff_letter": {"P_perdiem": .06, "P_goodthru": .04},
    "lien_release": {"L_early": .06, "L_state": .03, "L_address": .04},
    "statement_request": {"S_month": .02, "S_yearend": .05},
}


def build(seed=SEED):
    rng = random.Random(seed)
    flows = list(SHARES)
    w = [SHARES[f] for f in flows]
    rows, i = [], FIRST_ID
    for day in DAYS:
        for _ in range(PER_DAY + rng.randint(-25, 25)):
            f = rng.choices(flows, w)[0]
            hour = min(22, max(7, int(rng.gauss(14, 3.6))))
            ts = datetime(day.year, day.month, day.day, hour, rng.randint(0, 59))
            turns = max(1, int(rng.expovariate(1 / TURNS[f]) + 1))
            two = rng.random() < TWO_LOANS
            digits = two and f in LOAN_FLOWS and rng.random() < BY_DIGITS
            terr = rng.random() < TOOL_ERROR
            cause = None
            if digits and rng.random() < .5:
                cause = "X_wrongloan"
            elif terr and f in ("payoff_letter", "account_question", "fee_explanation") and rng.random() < INVENT:
                cause = "X_invent"
            elif not terr:
                u, acc = rng.random(), 0.0
                for c, p in CAUSES[f].items():
                    acc += p
                    if u < acc:
                        cause = c
                        break
            if cause:
                turns = int(turns * 1.8) + 4                 # failing conversations run long: the borrower pushes back
            abandoned = not terr and rng.random() < ABANDON
            r = {"trace_id": f"t-{i:06d}", "day": day.isoformat(), "started_at": ts.isoformat(timespec="minutes"),
                 "flow": f, "group": GROUP[f], "risk_tier": TIER[f], "turns": turns,
                 "handoff": int(f == "hardship" and rng.random() < .25 or rng.random() < .03),
                 "two_loans": two, "named_by_digits": digits, "tool_error": terr,
                 "status": "error" if terr else ("abandoned" if abandoned else "completed"),
                 "cause": cause, "offer_drafted": False, "offered_loan_recent_deferral": False,
                 "money_in_reply": f in ("payoff_letter", "account_question", "fee_explanation") and not (terr and cause is None)}
            if f == "hardship":
                r["offer_drafted"] = cause in (None, "X_wrongloan", "H_income", "H_approval") and rng.random() < .6
                if cause == "X_wrongloan" and r["offer_drafted"]:
                    r["offered_loan_recent_deferral"] = rng.random() < .3
            rows.append(r)
            i += 1
    return rows


def risk_fn(frame):
    """Chapter 3's risk score: 1 + 3 x high tier + turns over the flow's mean + hand-off."""
    mean = {}
    for r in frame:
        mean.setdefault(r["flow"], []).append(r["turns"])
    mean = {f: sum(v) / len(v) for f, v in mean.items()}
    return lambda r: 1 + 3 * (r["risk_tier"] == "high") + r["turns"] / mean[r["flow"]] + r["handoff"]


# monthly error-analysis draw: 50 traces in four quotas (Chapter 3's routine, made concrete)
QUOTAS = {"fee_explanation": 10, "payoff_letter": 8, "lien_release": 7, "hardship": 15,
          "account_question": 6, "statement_request": 4}

# what each of the 50 actually contains, by reading position; applied to the drawn rows so the
# frame, the census and the injection all see the same facts the notebook records
POSITION_FACTS = {
    2: dict(cause=None, tool_error=True, status="error", money_in_reply=False),
    3: dict(cause="F_waive"), 6: dict(cause="X_wrongloan", two_loans=True, named_by_digits=True),
    13: dict(cause="X_wrongloan", two_loans=True, named_by_digits=True),
    15: dict(cause="X_invent", tool_error=True, status="error", money_in_reply=True),
    21: dict(cause="L_address"),
    30: dict(cause="H_refused", offer_drafted=False),
    32: dict(cause="H_ignored"),
    33: dict(cause="X_wrongloan", two_loans=True, named_by_digits=True, offer_drafted=True,
              offered_loan_recent_deferral=True),
    34: dict(cause=None, tool_error=True, status="error", offer_drafted=False),
    43: dict(cause="X_invent", tool_error=True, status="error", money_in_reply=True),
    45: dict(cause=None), 48: dict(cause="S_yearend"),
}


def apply_facts(frame, drawn_ids):
    """drawn_ids in reading order; overwrite planted facts for the 50 and clear stray causes."""
    by = {r["trace_id"]: r for r in frame}
    for n, t in enumerate(drawn_ids, 1):
        r = by[t]
        base = dict(cause=None, tool_error=False, status="completed")
        if r["flow"] == "hardship":
            base.update(offered_loan_recent_deferral=False)
        if r["flow"] in ("payoff_letter", "account_question", "fee_explanation"):
            base.update(money_in_reply=True)
        r.update(base)
        r.update(POSITION_FACTS.get(n, {}))
    return frame


if __name__ == "__main__":
    from collections import Counter
    rows = build()
    print(len(rows), rows[0]["trace_id"], rows[-1]["trace_id"])
    print(Counter(r["flow"] for r in rows))
    print(Counter(r["cause"] for r in rows if r["cause"]))
    print(Counter(r["status"] for r in rows))
