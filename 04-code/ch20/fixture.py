"""Chapter 20 fixture: SIMULATED hardship decisions with three confidence fields.

Nothing here is model output. Every decision, its gold correctness, and the
three confidence values Compass and a judge would have written onto the trace
are planted from stated rates, seed 2026, so the chapter's arithmetic can be
checked. Truss computations on these values are real.

Unit: a hardship decision, meaning a drafted offer or a decline that Compass
proposes. Asks and referrals are not routed (an ask is a question; a referral
already goes to an officer).

Planted world (the chapter states these numbers as assumptions):
- kind: offer 70%, decline 30%; Spanish 14%.
- segments: anniversary 6.5%, stated change of work 5.6%, more than one loan 10%.
- chance the proposed decision is wrong: 2.5% baseline; 10% anniversary;
  30% stated work (FM-26, still a candidate); 6% more than one loan.
- a latent evidence strength z drives the action-token probability; wrong
  stated-work decisions carry high z (Compass used the record, confidently).
- verbalised confidence: Compass's stated 0-100 number, clustered at 92 and 95.
- logprob confidence: probability of the action label token, overconfident.
- judge-estimated confidence: a separate reader's probability that the
  decision is right; it shares Compass's weakness on anniversary dates.
- citation field: whether the reply cites the policy section and the account
  record; present on 97% of decisions, right or wrong.
- officers: catch 92% of wrong drafts they review (80% when the week's review
  load is over capacity) and introduce an error on 0.2% of right ones; on
  refused cases (no draft) they get 2% wrong.
- 2.5% of decisions carry no log-probability (the decision step was retried
  on a path that does not return one).
"""
from __future__ import annotations

import math
import random

SEED = 2026
MODEL_PIN_A = "compass-decision-2027-09"      # the build since rc-0917-3 (27 Sep 2027)
MODEL_PIN_B = "compass-decision-2028-02"      # rc-0214-1, Monday 14 February 2028
POLICY_DIGEST = "hp-2027-04+hb-2027-07"       # hardship policy and bulletins in force

P_WRONG = {"base": 0.025, "anniversary": 0.10, "stated_work": 0.30, "multi_loan": 0.06}
OFFICER_CATCH = 0.92
OFFICER_SLIP = 0.002
OFFICER_SCRATCH = 0.02
OFFICER_CATCH_OVERLOADED = 0.80
P_MISSING = 0.025
MINUTES = {"auto": 0.0, "review": 4.0, "refuse": 12.0}
WEEK_START_ID = {  # first trace ID of each production week (4,000 IDs a week at 10% traffic)
    "2028-01-03": 229201, "2028-01-10": 233201, "2028-01-17": 237201, "2028-01-24": 241201,
    "2028-01-31": 245201, "2028-02-07": 249201, "2028-02-14": 253201, "2028-02-21": 257201,
    "2028-02-28": 261201, "2028-03-06": 265201,
}


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def _one(rng, model="A"):
    seg = []
    if rng.random() < 0.065:
        seg.append("anniversary")
    if rng.random() < 0.056:
        seg.append("stated_work")
    if rng.random() < 0.10:
        seg.append("multi_loan")
    p = P_WRONG["base"]
    for s in seg:
        p = max(p, P_WRONG[s])
    correct = rng.random() >= p
    kind = "offer" if rng.random() < 0.70 else "decline"
    lang = "es" if rng.random() < 0.14 else "en"
    if correct:
        z = rng.gauss(1.7, 0.85)
    elif "stated_work" in seg:
        z = rng.gauss(1.35, 0.85)   # confident and wrong: the record said otherwise
    else:
        z = rng.gauss(-0.1, 1.0)
    shift = 4.2 if model == "A" else 5.4   # model B is sharper, same ranking
    logprob = sigmoid(2.1 * z + shift)
    # verbalised: clustered, weakly related to correctness
    u = rng.random()
    if correct:
        verbal = 0.95 if u < 0.40 else (0.92 if u < 0.92 else (0.98 if u < 0.97 else 0.85))
    else:
        verbal = 0.95 if u < 0.33 else (0.92 if u < 0.90 else (0.98 if u < 0.94 else 0.85))
    # judge-estimated: reads the trace; blind on anniversary dates, sees stated work
    zj = z + rng.gauss(0, 1.3)
    if not correct and "anniversary" in seg:
        zj = rng.gauss(1.6, 0.9)
    if not correct and "stated_work" in seg:
        zj = rng.gauss(-0.3, 0.9)
    judge = sigmoid(1.3 * zj + 0.9)
    citation = rng.random() < 0.97
    check_fail = rng.random() < (0.25 if not correct else 0.02)
    sw_flag = ("stated_work" in seg and rng.random() < 0.90) or (rng.random() < 0.01)
    flags = []
    if check_fail:
        flags.append("check_fail")
    if sw_flag:
        flags.append("stated_work")
    if rng.random() < P_MISSING:
        logprob = None   # decision step retried without log-probabilities
    return {"kind": kind, "lang": lang, "segments": seg, "correct": correct,
            "verbal": verbal, "logprob": logprob, "judge": judge, "citation": citation,
            "flags": flags, "u_officer": rng.random()}


def draw(n, rng, model="A", week=None, ids=None):
    out = []
    for i in range(n):
        c = _one(rng, model)
        c["week"] = week
        c["trace_id"] = ids[i] if ids else None
        out.append(c)
    return out


def outcome(case, route, overloaded=False):
    """True if what the borrower finally receives is wrong after this route.

    Overloaded officers (weekly review minutes above capacity) catch fewer
    wrong drafts: OFFICER_CATCH_OVERLOADED instead of OFFICER_CATCH.
    """
    u = case["u_officer"]
    if route == "auto":
        return not case["correct"]
    if route == "review":
        catch = OFFICER_CATCH_OVERLOADED if overloaded else OFFICER_CATCH
        return (u >= catch) if not case["correct"] else (u < OFFICER_SLIP)
    return u < OFFICER_SCRATCH  # refuse: officer works the case without a draft


def status_quo(case):
    """Harbor's rule before this chapter: every drafted offer to an officer, declines sent."""
    return ("review", "kind:offer") if case["kind"] == "offer" else ("auto", "kind:decline")


def _ids(rng, week, n):
    start = WEEK_START_ID[week]
    return [f"t-{x:06d}" for x in sorted(rng.sample(range(start, start + 4000), n))]


def world():
    rng = random.Random(SEED)
    fit = draw(372, rng, "A", week="2027-09-27..2027-12-26")
    jan = []
    for wk, n in (("2028-01-03", 200), ("2028-01-10", 200)):
        jan += draw(n, rng, "A", week=wk, ids=_ids(rng, wk, n))
    live = {}
    for wk in ("2028-01-17", "2028-01-24", "2028-01-31", "2028-02-07"):
        live[wk] = draw(140, rng, "A", week=wk, ids=_ids(rng, wk, 140))
    post = {}
    for wk in ("2028-02-14", "2028-02-21", "2028-02-28"):
        post[wk] = draw(140, rng, "B", week=wk, ids=_ids(rng, wk, 140))
    recal = []
    for wk, n in (("2028-02-14", 150), ("2028-02-21", 150)):
        recal += draw(n, rng, "B", week=wk, ids=_ids(rng, wk, n))
    return {"fit": fit, "jan": jan, "live": live, "post": post, "recal": recal}
