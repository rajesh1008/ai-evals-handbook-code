"""Chapter 16, REAL model run: the reply texts the judges read. The fixture holds facts, not text, so a
small fast model writes each Compass reply from a brief that fixes what it must say (including the
wrong content of planted failures) and its tone (warm or curt, assigned at random, independent of
correctness). Also: second replies for 80 pairwise cases, and Spanish versions of 100 test replies.
Model: claude-haiku-4-5-20251001 at the API's default sampling. Run: python3 gen.py run"""
import random
import sys

import fixture as F
import llm

TONE = {"warm": "warm and empathetic: acknowledge the borrower's frustration, apologise for the trouble, friendly sign-off line",
        "curt": "curt and bureaucratic: no apology, no empathy, short declarative sentences, polite but cold"}
REASON = {"no_autopay": "the loan is not enrolled in autopay, and the one-time courtesy waiver is only for autopay borrowers",
          "waiver_inside": "a courtesy waiver was already used on this loan within the last twelve months",
          "waiver_12_13": "a courtesy waiver was already used on this loan within the last twelve months"}
SAY = {
    "right_no": "The ${fee} late fee on the loan ending {asked} stands: the payment posted {days} days after the due date, past the 15-day grace period, and it cannot be waived because {reason}. Say how to avoid it next time.",
    "tool_bug": "The ${fee} late fee on the loan ending {asked} stands: the payment posted {days} days after the due date, past the 15-day grace period, and it cannot be waived because {reason}. Say how to avoid it next time.",
    "right_waive": "The ${fee} late fee on the loan ending {asked} is being waived as a one-time courtesy for autopay borrowers (one courtesy waiver every twelve months). It will be reversed; nothing to pay.",
    "defer_review": "A waiver request is already open on the loan ending {asked}. Do not say whether the ${fee} fee will be removed; say a loan officer will confirm within two business days.",
    "defer_tool": "Say you could not load the fee details for the loan ending {asked} just now, so a loan officer will review the late fee and confirm within two business days. Do not state any amount or status.",
    "F_waive": "State that the ${fee} late fee on the loan ending {asked} stands and cannot be waived, because the payment posted {days} days after the due date, past the 15-day grace period.",
    "F_hedge": "Without using the word 'waive', say the ${fee} late fee on the loan ending {asked} will stay on the statement because the payment posted {days} days after the due date, and that the borrower can call the servicing line if they want to ask about it.",
    "X_wrongloan": "State that the ${fee} late fee on the loan ending {asked} stands and cannot be waived, because the payment posted {days} days after the due date, past the 15-day grace period, and the loan already had its courtesy waiver this year.",
    "X_invent": "State that the ${fee} late fee on the loan ending {asked} stands and is final, because the payment was more than 15 days late.",
}
BRIEF = """You are writing one sample reply for a test fixture: what a loan-servicing chat assistant called Compass said to a borrower.
Borrower asked: {q}
The reply must say exactly this, in your own words, and nothing that contradicts it: {say}
Tone: {tone}. Length: about {words} words. Write only the reply text, with no subject line and no sign-off name."""


def brief(t, kind=None, words=None, tone=None):
    k = kind or t["kind"]
    say = SAY[k].format(fee=F.LATE_FEE, asked=t["asked"], days=t["days"],
                        reason=REASON.get(t["history"]["reason"] or "", REASON["waiver_inside"]))
    return BRIEF.format(q=F.question(t), say=say, tone=TONE[tone or t["tone"]], words=words or t["words"])


def req(prompt, max_tokens=700):
    return {"model": llm.SMALL, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}


def all_traces():
    dev, test = F.judge_set()
    bugs, normal = F.agent_set()
    seen, out = set(), []
    for t in dev + test + bugs + normal:
        if t["trace_id"] not in seen:
            seen.add(t["trace_id"]); out.append(t)
    return out


COUNTER = {"right_waive": "F_waive", "F_waive": "right_waive", "F_hedge": "right_waive",
           "defer_tool": "X_invent", "X_invent": "defer_tool"}


def pair_plan():
    """80 test traces: 40 contrast pairs (one right, one wrong reply on the same trace and span, same
    tone and length) and 40 equal pairs (same right decision, second reply about twice as long)."""
    _, test = F.judge_set()
    rng = random.Random(F.SEED + 7)
    contrast_pool = [t for t in test if t["kind"] in COUNTER]
    equal_pool = [t for t in test if t["kind"] in ("right_no", "right_waive")]
    con = sorted(rng.sample(contrast_pool, 40), key=lambda t: t["trace_id"])
    eq_ids = {t["trace_id"] for t in con}
    eq = sorted(rng.sample([t for t in equal_pool if t["trace_id"] not in eq_ids], 40), key=lambda t: t["trace_id"])
    return con, eq


def replies(live=False):
    return llm.run("replies", [(t["trace_id"], req(brief(t))) for t in all_traces()], live)


def alt_replies(live=False):
    con, eq = pair_plan()
    jobs = [(t["trace_id"], req(brief(t, kind=COUNTER[t["kind"]]))) for t in con]
    jobs += [(t["trace_id"], req(brief(t, words=t["words"] * 2))) for t in eq]
    return llm.run("alt_replies", jobs, live)


SPANISH = """Translate this reply from a loan-servicing chat assistant into the Spanish a US lender would use with a borrower in Arizona. Keep every number, date, loan digit and claim exactly as it is; do not add or remove anything. Write only the translation.

{reply}"""


def spanish_ids():
    _, test = F.judge_set()
    rng = random.Random(F.SEED + 11)
    return sorted(t["trace_id"] for t in rng.sample(test, 100))


def spanish(live=False):
    R = replies()
    return llm.run("spanish", [(i, req(SPANISH.format(reply=R[i]["text"]), 900)) for i in spanish_ids() if i in R], live)


if __name__ == "__main__":
    live = sys.argv[1:] == ["run"]
    R = replies(live)
    A = alt_replies(live)
    S = spanish(live)
    u = llm.usage(list(R.values()) + list(A.values()) + list(S.values()))
    print(f"replies {len(R)}, second replies {len(A)}, Spanish {len(S)}; tokens in {u['in']:,} out {u['out']:,}; about ${u['cost']:.2f}")
