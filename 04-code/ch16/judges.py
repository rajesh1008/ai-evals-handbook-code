"""Chapter 16, REAL model runs: the MC-02 judge and its variants, read against fee-judge-v1.
Each prompt is a function of one trace; each experiment is (tag, prompt, model, ids, repeat).
Run: python3 judges.py run [experiment ...]   (no argument: every experiment; no 'run': cache only)"""
import json
import re
import sys

import fixture as F
import gen
import llm

CARD_Q = ("Did the reply state a fee amount, grace period or waiver status that differs from what the "
          "fee tool returned, or would have returned, for the loan the borrower named?")


def block(t, reply, span=True):
    lines = [f'<trace id="{t["trace_id"]}">', f"Borrower: {F.question(t)}"]
    if span:
        lines.append(f"Fee tool span: {F.tool_span(t)}")
    lines += [f"Compass reply: {reply}", "</trace>"]
    return "\n".join(lines)


# J0: what a reader of the reply alone can see (no tool span).
def p_reply_only(t, reply):
    return ("You are reviewing a reply from Compass, a loan-servicing chat assistant, to a borrower asking about a late fee. "
            "Decide whether the reply gives the borrower wrong information about the fee amount, the grace period or whether "
            "the fee can be waived.\n\n" + block(t, reply, span=False) +
            '\n\nAnswer with JSON only: {"verdict": "pass"} if the information is right, {"verdict": "fail"} if it is wrong, '
            'or {"verdict": "cannot_tell"}.')


# V0: the card's question, as written for people, handed to a model.
def p_v0(t, reply):
    return ("You are checking a reply from Compass, a loan-servicing chat assistant, against the fee tool result in the same trace.\n\n"
            + block(t, reply) + f"\n\nQuestion: {CARD_Q}\n"
            'If yes, the verdict is fail; if no, pass. Answer with JSON only: {"verdict": "pass" | "fail" | "cannot_tell"}')


RULES_V1 = """You are checking one reply from Compass, Harbor Lending's loan-servicing assistant, against the fee tool result logged in the same trace. This is check MC-02 (wrong fee explanation).

Question: {q}

How to decide:
1. Loan. Compare the loan number in the tool call with the loan the borrower named. If they differ, every fee detail in the reply came from the wrong loan: fail, unless the reply states no fee details at all.
2. Tool error. If the tool returned an error, the reply has nothing to rely on. If it says the fee stands, is final, or states any waiver status, fail. If it defers to a person without stating them, pass.
3. Otherwise compare the reply with the tool result field by field:
   - late_fee and grace_days: any different amount or number of days is a fail.
   - courtesy_waiver "eligible": the fee is to be waived. A reply that says the fee stays, stands, remains on the statement or cannot be waived states a different waiver status, even if it offers a call: fail.
   - courtesy_waiver "not_eligible": the fee stands; a reply that says so passes. The tool does not log the reason. A reason the reply gives (no autopay, a waiver already used this year) is not a different status; judge the status, not the reason.
   - courtesy_waiver "request_open": a decision is pending; a reply that defers to a loan officer passes.
4. Tone, warmth, apology, length and style are not part of this check. A cold reply with the right facts passes; a kind reply with a wrong fact fails.
5. Use cannot_tell only if the trace lacks something you need to decide.

{trace}

{tail}"""
TAIL_CRITIQUE = ('First write a critique of at most four sentences: name what the reply states about the loan, amount, grace period and waiver, '
                 'and what the tool returned. Then, on the last line, output JSON only: {"verdict": "pass" | "fail" | "cannot_tell"}')
TAIL_VERDICT = 'Answer with JSON only, no other text: {"verdict": "pass" | "fail" | "cannot_tell"}'


def p_v1(t, reply):
    return RULES_V1.format(q=CARD_Q, trace=block(t, reply), tail=TAIL_CRITIQUE)


def p_verdict_only(t, reply):
    return RULES_V1.format(q=CARD_Q, trace=block(t, reply), tail=TAIL_VERDICT)


# Failure injection: a rubric that lets the judge grade the tone instead of the facts.
def p_tone(t, reply):
    return ("You are checking the quality of a reply from Compass, a loan-servicing chat assistant, to a borrower asking about a late fee.\n\n"
            + block(t, reply) +
            "\n\nA good reply is clear, polite, empathetic and helpful, explains the fee in plain language and leaves the borrower "
            "feeling respected. A bad reply is cold, confusing or dismissive.\n"
            'First write a critique of at most four sentences. Then, on the last line, output JSON only: {"verdict": "pass" | "fail" | "cannot_tell"}')


PAIR = """You are comparing two replies from Compass, Harbor Lending's loan-servicing assistant, to the same borrower in the same trace. The fee tool result is logged below.

Borrower: {q}
Fee tool span: {span}

Reply A: {a}

Reply B: {b}

Which reply better answers the borrower, given what the fee tool returned? Judge correctness of the fee amount, grace period, waiver status and loan first; then clarity.
First write a critique of at most four sentences. Then, on the last line, output JSON only: {{"better": "A" | "B" | "tie"}}"""


def p_pair(t, a, b):
    return PAIR.format(q=F.question(t), span=F.tool_span(t), a=a, b=b)


def req(prompt, model=llm.SMALL, rep=0, thinking=False):
    r = {"model": model, "max_tokens": 600, "messages": [{"role": "user", "content": prompt}]}
    if thinking:
        r["max_tokens"] = 3000
        r["thinking"] = {"type": "enabled", "budget_tokens": 1024}
    if rep:
        r["metadata"] = {"user_id": f"ch16-repeat-{rep}"}  # repeats differ only in metadata, so each is a fresh draw
    return r


def verdict(text, field="verdict"):
    m = re.findall(r"\{[^{}]*\}", text or "")
    for s in reversed(m):
        try:
            v = json.loads(s).get(field)
            if v:
                return str(v).strip().lower() if field == "verdict" else str(v).strip()
        except json.JSONDecodeError:
            continue
    return "unparsed"


def sets():
    dev, test = F.judge_set()
    bugs, normal = F.agent_set()
    return dev, test, bugs, normal


def experiments():
    dev, test, bugs, normal = sets()
    R = gen.replies()
    S = gen.spanish()
    A = gen.alt_replies()
    E = {}

    def add(name, prompt, traces, model=llm.SMALL, rep=0, thinking=False, text=None):
        text = text or R
        E[name] = [(t["trace_id"], req(prompt(t, text[t["trace_id"]]["text"]), model, rep, thinking)) for t in traces if t["trace_id"] in text]

    add("dev_j0", p_reply_only, dev)
    add("dev_v0", p_v0, dev)
    add("dev_v1", p_v1, dev)
    add("test_j0", p_reply_only, test)
    add("test_v0", p_v0, test)
    for rep in (0, 1, 2):
        add(f"test_v1_small_r{rep}", p_v1, test, rep=rep)
    add("test_v1_large", p_v1, test, model=llm.LARGE)
    add("test_v1_think", p_v1, test, thinking=True)
    add("test_verdict_only", p_verdict_only, test)
    add("test_tone", p_tone, test)
    sp = [t for t in test if t["trace_id"] in S]
    add("test_v1_spanish", p_v1, sp, text=S)
    con, eq = gen.pair_plan()
    add("alt_v1_small", p_v1, con + eq, text=A)
    pairs = []
    for t in con + eq:
        o, a = R[t["trace_id"]]["text"], A[t["trace_id"]]["text"]
        pairs.append((t["trace_id"] + ":OA", req(p_pair(t, o, a))))
        pairs.append((t["trace_id"] + ":AO", req(p_pair(t, a, o))))
    E["pairs_small"] = pairs
    add("bugs_v1_small", p_v1, bugs)
    add("bugs_v1_large", p_v1, bugs, model=llm.LARGE)
    return E


def load_all(live=False, only=None):
    out = {}
    for name, jobs in experiments().items():
        if only and name not in only:
            out[name] = llm.run("judge", jobs, False)
            continue
        out[name] = llm.run("judge", jobs, live)
    return out


if __name__ == "__main__":
    live = len(sys.argv) > 1 and sys.argv[1] == "run"
    only = sys.argv[2:] or None
    res = load_all(live, only)
    for k, v in res.items():
        u = llm.usage(v.values())
        print(f"{k:22s} {len(v):4d} calls  in {u['in']:>8,} out {u['out']:>7,}  ${u['cost']:.3f}")
