"""Chapter 6 fixture: Compass traces from Mon 4 to Sun 31 January 2027, with planted causes,
first coders' free-text notes, and the evidence an inclusion test reads.

Every number in the chapter comes from running lab.py on this fixture (seed 2026). The causes
are planted; the coders and their confusions are simulated and documented in CODERS below.
Assumptions carried from the ledger: traffic continued at the pilot rate (about 572 a day,
IDs continue from t-024011 through November and December to t-068031 on 4 January), the
loan-officer queue is staffed 08:00 to 19:00 Phoenix time, and the extension fix (after
5 November) told Compass to count any payment extension as a prior deferral.
"""
import random
from datetime import date, datetime, timedelta

SEED = 2026
FIRST_ID = 68031
DAYS = [date(2027, 1, 4) + timedelta(d) for d in range(28)]
PER_DAY = 572
SHARES = {"account_question": .39, "fee_explanation": .20, "statement_request": .19,
          "payoff_letter": .10, "lien_release": .06, "hardship": .06}
TIER = {"account_question": "low", "statement_request": "low", "fee_explanation": "medium",
        "payoff_letter": "medium", "lien_release": "medium", "hardship": "high"}
TURNS = {"account_question": 3.6, "fee_explanation": 6.5, "hardship": 13.5, "lien_release": 7.6,
         "payoff_letter": 5.5, "statement_request": 3.6}
QUEUE_OPEN, QUEUE_CLOSE = 8, 19

# planted per-trace probabilities of each cause, by flow; at most one cause per trace.
# H_second is zero: the early-December extension fix stopped second deferrals and caused H_refused.
CAUSES = {
    "hardship": {"H_income": .035, "H_ignored": .03, "H_approval": .015, "H_second": 0.0,
                 "H_refused": .055, "H_bereave": .006},   # H_closed, H_spanish conditional below
    "fee_explanation": {"F_waive": .04},                   # F_tenday: cause removed 16 Dec
    "account_question": {"A_date": .045, "A_second": .03},
    "payoff_letter": {"P_perdiem": .06, "P_goodthru": .04},
    "lien_release": {"L_early": .06, "L_state": .03, "L_address": .04},
    "statement_request": {"S_month": .02},                 # S_yearend by week below
}
P_CLOSED = .20     # out-of-hours hardship conversation asking for a person, no callback offered
P_SPANISH = .25    # Spanish hardship conversation whose request for a person is missed
SPANISH = .10      # share of hardship conversations in Spanish
YEAREND = {1: .22, 2: .16, 3: .10, 4: .07}   # year-end statement requests sent a monthly, by week

NOTES = {
    "H_income": ["offer drafted before {b} confirmed income, income question came after the offer",
                 "plan offered first, income asked later, no income confirmation before offer"],
    "H_ignored": ["{b} asked for a loan officer twice, kept getting plan options, queue was open",
                  "wanted to talk to a real person, assistant kept offering plan options instead"],
    "H_closed": ["handoff tool returned queue closed after hours, reply gave no callback time",
                 "after hours, queue closed, no callback offered, conversation just ended"],
    "H_spanish": ["wrote in spanish hablar con una persona, router stayed in hardship flow",
                  "spanish request quiero hablar con alguien missed, stayed in hardship flow"],
    "H_approval": ["offer sent without loan officer approval sentence"],
    "H_second": ["deferral offered though prior deferral {m} months ago"],
    "H_refused": ["refused deferral, cited payment extension from {y} as prior deferral, tool said eligible",
                  "eligible per tool but refused, old extension counted as deferral, over twelve months"],
    "H_bereave": ["husband on the loan died, treated as normal hardship, no estate team",
                  "co-borrower passed away, ordinary hardship script, asked for income"],
    "F_waive": ["fee should have been waived per policy, reply defended fee"],
    "A_date": ["balance quoted as of wrong date"],
    "A_second": ["second loan ignored, answered about one loan only"],
    "P_perdiem": ["payoff quote missing per diem interest", "per diem left out of payoff amount"],
    "P_goodthru": ["good-through date wrong on payoff quote", "payoff good through date off"],
    "L_early": ["release promised before title office date"],
    "L_state": ["wrong title state on release"],
    "L_address": ["release letter mailed to old address borrower said had changed"],
    "S_month": ["wrong month sent, {m1} instead of {m2}"],
    "S_yearend": ["asked for year-end interest statement for taxes, got december monthly",
                  "wanted 2026 interest paid statement for tax return, sent monthly statement"],
}
CODERS = """First coders: Grace Holloway on hardship, the evaluation lead on the other five flows.
Second coders: Ben Fletcher on hardship, Ryan Mitchell on the other flows.
Simulated confusions (second coder only): under v0.1, FM-09 and FM-10 swapped half the time;
year-end statements coded FM-13 60% of the time (otherwise 'none fits'); wrong refusals coded
FM-04 half the time; under v0.2, FM-14 and FM-15 swapped 15% of the time and FM-20 coded FM-04 10% of the time. The first coder
codes a trace to the v0.1 mode its symptom most resembles when one is close (FM-02 for any
missed person, FM-13 for any wrong statement) and writes 'none fits' otherwise."""


def build(seed=SEED):
    rng = random.Random(seed)
    flows = list(SHARES)
    w = [SHARES[f] for f in flows]
    rows, i = [], FIRST_ID
    for day in DAYS:
        week = (day - DAYS[0]).days // 7 + 1
        for _ in range(PER_DAY + rng.randint(-25, 25)):
            f = rng.choices(flows, w)[0]
            hour = min(22, max(7, int(rng.gauss(14, 3.6))))
            ts = datetime(day.year, day.month, day.day, hour, rng.randint(0, 59))
            turns = max(1, int(rng.expovariate(1 / TURNS[f]) + 1))
            lang = "es" if (f == "hardship" and rng.random() < SPANISH) else "en"
            handoff = int(f == "hardship" and rng.random() < .25 or rng.random() < .03)
            cause = None
            u, acc = rng.random(), 0.0
            for c, p in CAUSES[f].items():
                acc += p
                if u < acc:
                    cause = c
                    break
            if f == "hardship" and cause is None:
                if not (QUEUE_OPEN <= hour < QUEUE_CLOSE) and rng.random() < P_CLOSED:
                    cause = "H_closed"
                elif lang == "es" and rng.random() < P_SPANISH:
                    cause = "H_spanish"
            if f == "statement_request" and cause is None and rng.random() < YEAREND[week]:
                cause = "S_yearend"
            r = {"trace_id": f"t-{i:06d}", "day": day.isoformat(), "started_at": ts.isoformat(timespec="minutes"),
                 "week": week, "flow": f, "risk_tier": TIER[f], "turns": turns, "handoff": handoff,
                 "lang": lang, "cause": cause, "note": None, "msg": ""}
            if f == "statement_request":
                yearend = cause == "S_yearend" or rng.random() < .05
                r["requested_doc"] = "year_end" if yearend else "monthly"
                r["requested_period"] = "2026" if yearend else rng.choice(["2026-10", "2026-11", "2026-12"])
                if cause == "S_yearend":
                    r["sent_doc"], r["sent_period"] = "monthly", "2026-12"
                elif cause == "S_month":
                    r["sent_doc"] = "monthly"
                    r["sent_period"] = {"2026-10": "2026-09", "2026-11": "2026-10", "2026-12": "2026-11"}.get(r["requested_period"], "2026-11")
                    if r["requested_doc"] != "monthly":
                        r["requested_doc"], r["requested_period"] = "monthly", "2026-12"
                else:
                    r["sent_doc"], r["sent_period"] = r["requested_doc"], r["requested_period"]
            if f == "hardship":
                if cause == "H_bereave":
                    r["msg"] = rng.choice(["my husband passed away in december and he was on the loan",
                                           "my wife died last month, the car loan was in both our names",
                                           "co-signer passed away, what happens to the loan now"])
                elif rng.random() < .012:
                    r["msg"] = rng.choice(["had to pay for my father's funeral so i'm short this month",
                                           "funeral costs for my aunt wiped out savings"])
                else:
                    r["msg"] = rng.choice(["lost hours at work", "car repair bill", "medical bills",
                                           "can i skip a payment", "reduced income this month"])
            if cause:
                r["note"] = rng.choice(NOTES[cause]).format(b="borrower", m=rng.randint(3, 11),
                                                            y=rng.choice(["2024", "2025"]),
                                                            m1="november", m2="december")
            rows.append(r)
            i += 1
    # the complained-about conversation (complaint received Tue 19 Jan 2027)
    cand = [r for r in rows if r["cause"] == "H_bereave" and r["day"] == "2027-01-12"]
    if not cand:
        cand = [r for r in rows if r["flow"] == "hardship" and r["day"] == "2027-01-12" and r["cause"] is None][:1]
        cand[0].update(cause="H_bereave", note=NOTES["H_bereave"][0],
                       msg="my husband passed away in december and he was on the loan")
    cand[0]["complaint"] = "2027-01-19"
    return rows


CLOSEST_V01 = {"H_ignored": "FM-02", "H_closed": "FM-02", "H_spanish": "FM-02", "S_yearend": "FM-13",
               "H_income": "FM-01", "H_approval": "FM-03", "H_second": "FM-04", "F_tenday": "FM-05",
               "F_waive": "FM-06", "A_date": "FM-07", "A_second": "FM-08", "P_perdiem": "FM-09",
               "P_goodthru": "FM-10", "L_early": "FM-11", "L_state": "FM-12", "S_month": "FM-13"}
CLOSEST_V02 = {"H_ignored": "FM-14", "H_closed": "FM-15", "H_spanish": "FM-16", "S_yearend": "FM-18",
               "S_month": "FM-17", "P_perdiem": "FM-19", "P_goodthru": "FM-19", "H_refused": "FM-20",
               "H_bereave": "FM-21", "H_income": "FM-01", "H_approval": "FM-03", "H_second": "FM-04",
               "F_waive": "FM-06", "A_date": "FM-07", "A_second": "FM-08", "L_early": "FM-11",
               "L_state": "FM-12", "F_tenday": "FM-05"}


def first_coder(r, version):
    return (CLOSEST_V01 if version.startswith("0.1") else CLOSEST_V02).get(r["cause"])


def second_coder(r, version, rng):
    c = first_coder(r, version)
    if version.startswith("0.1"):
        if c in ("FM-09", "FM-10") and rng.random() < .5:
            return {"FM-09": "FM-10", "FM-10": "FM-09"}[c]
        if r["cause"] == "S_yearend":
            return "FM-13" if rng.random() < .6 else None
        if r["cause"] == "H_refused":
            return "FM-04" if rng.random() < .5 else None
    else:
        if c in ("FM-14", "FM-15") and rng.random() < .15:
            return {"FM-14": "FM-15", "FM-15": "FM-14"}[c]
        if c == "FM-20" and rng.random() < .1:
            return "FM-04"
    return c


if __name__ == "__main__":
    rows = build()
    from collections import Counter
    print(len(rows), rows[0]["trace_id"], rows[-1]["trace_id"])
    print(Counter(r["flow"] for r in rows))
    print(Counter(r["cause"] for r in rows if r["cause"]))
