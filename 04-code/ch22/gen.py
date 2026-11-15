"""Chapter 22, REAL model run: the Compass reply each trace contains. The fixture holds facts, not
text, so a small fast model writes each reply from a brief that fixes what it must say (including
the wrong content of planted failures) and its tone. Model: claude-haiku-4-5-20251001, API default
sampling. Run: python3 gen.py run   (without 'run' it reads the cache only)."""
import sys

import fixture as F
import llm

TONE = {"warm": "warm and empathetic: acknowledge the frustration, apologise for the trouble, friendly closing line",
        "curt": "curt and bureaucratic: no apology, short declarative sentences, polite but cold"}


def say(t):
    k, a, d = t["kind"], t["asked"], t["days"]
    base = f"The payment on the loan ending {a} posted {d} days after the due date, past the 15-day grace period, so a ${F.LATE_FEE} late fee was assessed."
    if k == "stand_noauto":
        return base + " The fee stands and cannot be waived, because the loan is not enrolled in autopay and the courtesy waiver is only for autopay borrowers. Say how to avoid it next time."
    if k == "stand_inside":
        return base + f" The fee stands and cannot be waived, because a courtesy waiver was already applied on this loan on {t['waiver']}, and only one is allowed in any twelve months. Say how to avoid it next time."
    if k == "waive_ok":
        return base + " As an autopay borrower with no courtesy waiver used in the last twelve months, the fee is being waived as a one-time courtesy and will be reversed. Nothing to pay."
    if k == "waive_hb":
        return base + " Because this is the payment that triggered the borrower's approved hardship plan, the late fee is waived automatically under the hardship programme and will be reversed. Nothing to pay."
    if k == "defer_open":
        return f"A waiver request is already open on the loan ending {a}. Do not say whether the ${F.LATE_FEE} fee will be removed; say a loan officer will confirm within two business days."
    if k == "F_stand_elig":
        if t["waiver"]:
            return base + f" The fee stands and cannot be waived, because a courtesy waiver was already applied on this loan on {t['waiver']}, within the last twelve months."
        return base + " The fee stands and cannot be waived, because a courtesy waiver was already used on this loan this year."
    if k == "F_waive_inside":
        return base + " As an autopay borrower, the fee is being waived as a one-time courtesy and will be reversed. Nothing to pay."
    if k == "F_hb_stand":
        why = ("the loan is not enrolled in autopay and the courtesy waiver is only for autopay borrowers" if not t["autopay"]
               else f"a courtesy waiver was already applied on this loan on {t['waiver']}, and only one is allowed in any twelve months"
               if t["waiver"] else "late fees are charged on every payment posted after the grace period")
        return base + f" The fee stands and cannot be waived, because {why}."
    if k == "X_wrongloan":
        return base + f" The fee stands and cannot be waived, because a courtesy waiver was already applied on this loan on {t['hist_other']['waiver']}, and only one is allowed in any twelve months."
    if k == "F_terms":
        return (f"The payment on the loan ending {a} posted {d} days after the due date. Harbor's grace period is 10 days, so any payment "
                f"more than 10 days late is charged the ${F.LATE_FEE} late fee. The fee stands. Say how to avoid it next time.")
    raise KeyError(k)


BRIEF = """You are writing one sample reply for a test fixture: what a loan-servicing chat assistant called Compass said to a borrower.
Borrower asked: {q}
The reply must say exactly this, in your own words, and nothing that contradicts it: {say}
Tone: {tone}. Length: about {words} words. Write only the reply text, with no subject line and no sign-off name."""


def req(prompt, max_tokens=600):
    return {"model": llm.SMALL, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}


def replies(live=False):
    jobs = [(t["trace_id"], req(BRIEF.format(q=F.question(t), say=say(t), tone=TONE[t["tone"]], words=t["words"])))
            for t in F.study_set()]
    return llm.run("replies", jobs, live)


if __name__ == "__main__":
    R = replies(sys.argv[1:] == ["run"])
    u = llm.usage(R.values())
    print(f"replies {len(R)}; tokens in {u['in']:,} out {u['out']:,}; about ${u['cost']:.2f}")
