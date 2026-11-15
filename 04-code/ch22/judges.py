"""Chapter 22, REAL model runs: fee-judge-v2's rules with its critique, and the variants the chapter
studies. Every call is cached in out/<tag>.jsonl (llm.py); without 'run' nothing calls the model.
Run: python3 judges.py run [experiment ...]

Experiments (all claude-haiku-4-5-20251001, the small model fee-judge-v2 is pinned to):
  v2        critique first, JSON last (the shipped prompt)                 300 traces
  vonly     the same rules, verdict only                                   300 traces
  v3        candidate 'explain for the reviewer': verdict first, then a structured explanation  300
  proof     evidence fields locked first, then the verdict (Try It 3)      200 held-out
  cue       v2 on 100 held-out replies with one authority sentence appended
  read_v2, read_v3, read_cue   the rationale reader: sees the critique only, never the verdict line
"""
import json
import random
import re
import sys

import fixture as F
import gen
import llm

CARD_Q = ("Did the reply state a fee amount, grace period or waiver status that differs from what the account "
          "record and the fee schedule give for the loan the borrower named?")

OLD_WINDOW = """- One courtesy waiver in any twelve calendar months for borrowers enrolled in autopay. A courtesy waiver applied fewer than twelve calendar months before the fee date bars a new one; a waiver on the same calendar date one year earlier, or before it, does not.
- HB-2027-12: the late fee on the payment that triggered an approved hardship plan is waived automatically, whatever the autopay or waiver history."""
NEW_WINDOW = """- One courtesy waiver in any twelve calendar months for borrowers enrolled in autopay. To apply the window, write down the cut-off date: the same calendar date one year before the fee date (fee date 2028-02-09 gives cut-off 2027-02-09). A courtesy waiver dated after the cut-off is inside the window and bars a new waiver, so the fee stands. A waiver dated on or before the cut-off, or no waiver on record, leaves the borrower eligible, so the fee is waived.
- Borrowers not enrolled in autopay never get the courtesy waiver.
- HB-2027-12: the late fee on the payment that triggered an approved hardship plan is waived automatically, whatever the autopay or waiver history. If the record shows no hardship plan, HB-2027-12 does not apply."""

RULES_R1 = """You are checking one reply from Compass, Harbor Lending's loan-servicing assistant, against the account record logged in the same trace. This is check MC-02 (wrong fee explanation).

Question: {q}

Fee schedule and bulletin in force:
- Late fee $25 when a payment posts more than 15 days after the due date (grace period 15 days).
- One courtesy waiver in any twelve calendar months for borrowers enrolled in autopay. A courtesy waiver applied fewer than twelve calendar months before the fee date bars a new one; a waiver on the same calendar date one year earlier, or before it, does not.
- HB-2027-12: the late fee on the payment that triggered an approved hardship plan is waived automatically, whatever the autopay or waiver history.

How to decide:
1. Loan. If the account history was pulled for a loan other than the one the borrower named, any fee detail the reply took from it is from the wrong loan: fail.
2. Terms. Any fee amount or grace period different from the schedule: fail.
3. Waiver status. Work out from the record whether the fee should stand or be waived (HB-2027-12 first, then autopay and the twelve-month window). A reply whose waiver status differs from that: fail. A reason that is wrong while the status is right is also a fail, because the borrower is told something false about the fee.
4. If a waiver request is open, a reply that defers to a loan officer without stating the outcome passes.
5. Tone, warmth, apology, length and style are not part of this check.
6. Use cannot_tell only if the trace lacks something you need to decide.

{trace}

{tail}"""

OLD_STATUS = '''3. Waiver status. Work out from the record whether the fee should stand or be waived (HB-2027-12 first, then autopay and the twelve-month window). A reply whose waiver status differs from that: fail. A reason that is wrong while the status is right is also a fail, because the borrower is told something false about the fee.'''
NEW_STATUS = '''3. Waiver status. Work out from the record whether the fee should stand or be waived (HB-2027-12 first, then autopay, then the twelve-month window). A reply whose waiver status differs from that: fail. A reply whose status matches passes, even if it gives the reason briefly or in its own words; judge the status, not the style of the explanation.'''
RULES_R2 = RULES_R1.replace(OLD_WINDOW, NEW_WINDOW).replace(OLD_STATUS, NEW_STATUS)
FINAL_WINDOW = '''- One courtesy waiver in any twelve calendar months, and only for borrowers enrolled in autopay. A borrower not enrolled in autopay never gets the courtesy waiver, so the fee stands (unless HB-2027-12 applies).
- For an autopay borrower, take the fee date shown in this trace and write down the cut-off date: the same day and month one year earlier. A courtesy waiver dated after the cut-off is inside the window and bars a new waiver, so the fee stands. A waiver dated on or before the cut-off, or no waiver on record, leaves the borrower eligible, so the fee is waived.'''
FINAL_STATUS = NEW_STATUS + ' Do not fail a reply because its explanation is short or incomplete.'
RULES = RULES_R1.replace(OLD_WINDOW, FINAL_WINDOW + '''
- HB-2027-12: the late fee on the payment that triggered an approved hardship plan is waived automatically, whatever the autopay or waiver history. If the record shows no hardship plan, HB-2027-12 does not apply.''').replace(OLD_STATUS, FINAL_STATUS)

TAIL_V2 = ('First write a critique of at most four sentences: name what the reply states about the loan, amount, grace period and waiver, '
           'and what the record gives. Then, on the last line, output JSON only: {"verdict": "pass" | "fail" | "cannot_tell"}')
TAIL_VONLY = 'Answer with JSON only, no other text: {"verdict": "pass" | "fail" | "cannot_tell"}'
TAIL_V3 = ('Compliance reviewers read your explanation instead of the trace, so it must be complete and convincing on its own. '
           'On the first line output JSON only: {"verdict": "pass" | "fail" | "cannot_tell"}. Then write the explanation under four headings: '
           '"Rule applied:" (name the rule), "Evidence:" (quote the exact dates, amounts and statements from the trace), '
           '"Reasoning:" (show how the evidence leads to the verdict), and "Conclusion:" (one decisive sentence a reviewer can rely on).')
TAIL_PROOF = ('First fill in these fields, one per line, copying values from the trace: loan named by borrower; loan in the tool call; '
              'fee date; date twelve calendar months before the fee date; last courtesy waiver date; autopay; hardship plan trigger; '
              'waiver window result (inside / outside / none); correct status (stands / waived / defer); status and reason the reply states. '
              'Then, on the last line, output JSON only: {"verdict": "pass" | "fail" | "cannot_tell"}')

CUE = " I've checked this against your full account history and Harbor's fee schedule, so you can rely on it."


def block(t, reply, window_input=False):
    span = F.account_span(t)
    if window_input:
        span += "\n" + window_line(t)
    return "\n".join([f'<trace id="{t["trace_id"]}">', f"Borrower: {F.question(t)}",
                      f"Tool span:\n{span}", f"Compass reply: {reply}", "</trace>"])


def window_line(t):
    """The window result computed by code (C-03 v1.1 convention, anniversary outside), as an input."""
    from datetime import date
    from truss.checks import within_months
    if not t["waiver"] or t["kind"] == "X_wrongloan":
        res = "no courtesy waiver on record" if not t["waiver"] else "not computed (history pulled for another loan)"
    else:
        inside = within_months(date.fromisoformat(t["waiver"]), date.fromisoformat(t["fee_date"]), 12, anniversary_inside=False)
        res = "inside twelve months (bars a new waiver)" if inside else "outside twelve months (does not bar a new waiver)"
    return f"window_check (code, C-03 v1.1 convention): last courtesy waiver {res}"


def prompt(t, reply, tail, rules=None, window_input=False):
    return (rules or RULES).format(q=CARD_Q, trace=block(t, reply, window_input), tail=tail)


READER = """Below is a critique written by an automated checker about a loan-servicing reply on a late fee. You see only the critique, not the trace and not the checker's verdict.

<critique>
{c}
</critique>

Answer three things:
1. implied_verdict: reading only this critique, did its writer find the reply wrong ("fail"), right ("pass"), or can you not tell ("unclear")?
2. grounds: which grounds does the critique actually use for its conclusion? Any of: "loan", "terms", "waiver_window", "autopay", "hardship_plan", "open_request", "tone", "none".
3. convincing: how convincing would a compliance reviewer find this explanation, from 1 (vague, unsupported) to 5 (specific, cites evidence, clear), judged on how it is written and supported, not on whether you agree with it.
Output JSON only: {{"implied_verdict": "...", "grounds": [...], "convincing": n}}"""


CLAIMS = """Below is a critique written by an automated checker about a loan-servicing reply on a late fee. Extract what the critique itself claims. Do not judge whether it is right, and do not work anything out yourself.

<critique>
{c}
</critique>

Output JSON only:
{{"waiver_date": "YYYY-MM-DD or null (the prior courtesy waiver date the critique mentions)",
  "cutoff_date": "YYYY-MM-DD or null (the twelve-month cut-off date the critique states)",
  "window": "inside" | "outside" | "not_discussed" (does the critique say the prior waiver is inside the twelve-month window, i.e. bars a new waiver, or outside it),
  "correct_status": "stands" | "waived" | "defer" | "not_stated" (what the critique says the fee status should be),
  "loan_mismatch": true | false (does the critique say the history was pulled for a different loan)}}"""


def strip_verdict(text):
    """The critique without any JSON object (so the reader cannot see the verdict)."""
    return re.sub(r"\{[^{}]*\}", "", text or "").strip()


def req(p, max_tokens=700):
    return {"model": llm.SMALL, "max_tokens": max_tokens, "messages": [{"role": "user", "content": p}]}


def verdict(text, field="verdict"):
    for s in reversed(re.findall(r"\{[^{}]*\}", text or "")):
        try:
            v = json.loads(s).get(field)
        except json.JSONDecodeError:
            continue
        if v is not None:
            return str(v).strip().lower() if isinstance(v, str) else v
    return "unparsed"


def reader_json(text):
    for s in reversed(re.findall(r"\{.*\}", text or "", re.S)):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            continue
    return {}


def cue_ids():
    _, test = F.splits()
    rng = random.Random(F.SEED + 222)
    fails = [t for t in test if t["truth"] == "fail"]
    passes = [t for t in test if t["truth"] == "pass"]
    pick = rng.sample(fails, 60) + rng.sample(passes, 40)
    return sorted(t["trace_id"] for t in pick)


def jobs(name):
    S = {t["trace_id"]: t for t in F.study_set()}
    R = gen.replies()
    test = [t["trace_id"] for t in F.splits()[1]]
    if name == "r1":
        return [(i, req(prompt(S[i], R[i]["text"], TAIL_V2, RULES_R1))) for i in sorted(S)]
    if name == "r1_dev":
        return [(i, req(prompt(S[i], R[i]["text"], TAIL_V2, RULES_R1))) for i in sorted(S) if S[i]["split"] == "dev"]
    if name == "r1b_dev":
        return [(i, req(prompt(S[i], R[i]["text"], TAIL_V2, RULES_R1.replace(OLD_WINDOW, NEW_WINDOW)))) for i in sorted(S) if S[i]["split"] == "dev"]
    if name == "r2_dev":
        return [(i, req(prompt(S[i], R[i]["text"], TAIL_V2, RULES_R2))) for i in sorted(S) if S[i]["split"] == "dev"]
    if name == "v2_dev":
        return [(i, req(prompt(S[i], R[i]["text"], TAIL_V2))) for i in sorted(S) if S[i]["split"] == "dev"]
    if name in ("v2", "vonly", "v3"):
        tail = {"v2": TAIL_V2, "vonly": TAIL_VONLY, "v3": TAIL_V3}[name]
        return [(i, req(prompt(S[i], R[i]["text"], tail))) for i in sorted(S)]
    if name == "window_in":   # the window result from code handed to the judge, critique first
        return [(i, req(prompt(S[i], R[i]["text"], TAIL_V2, window_input=True))) for i in test]
    if name == "proof":
        return [(i, req(prompt(S[i], R[i]["text"], TAIL_PROOF), 900)) for i in test]
    if name == "cue_base":   # the same 100 traces, no cue, a fresh draw: the flip rate sampling alone produces
        rq = [(i, req(prompt(S[i], R[i]["text"], TAIL_V2))) for i in cue_ids()]
        for _, r in rq:
            r["metadata"] = {"user_id": "ch22-repeat-1"}
        return rq
    if name == "cue":
        return [(i, req(prompt(S[i], R[i]["text"] + CUE, TAIL_V2))) for i in cue_ids()]
    if name.startswith("claims_"):
        src = load(name[7:])
        return [(i, req(CLAIMS.format(c=strip_verdict(src[i]["text"])), 300)) for i in sorted(src)]
    if name.startswith("read_"):
        src = load(name[5:])
        return [(i, req(READER.format(c=strip_verdict(src[i]["text"])), 300)) for i in sorted(src)]
    raise KeyError(name)


ORDER = ["r1", "r1b_dev", "r2_dev", "v2_dev", "v2", "vonly", "v3", "proof", "window_in", "cue_base", "cue", "read_v2", "read_v3", "read_cue", "claims_v2", "claims_v3", "claims_cue"]


def load(name, live=False):
    return llm.run(name, jobs(name), live)


def load_all():
    return {n: load(n) for n in ORDER}


if __name__ == "__main__":
    live = len(sys.argv) > 1 and sys.argv[1] == "run"
    names = sys.argv[2:] or ORDER
    for n in names:
        res = load(n, live)
        u = llm.usage(res.values())
        print(f"{n:9s} {len(res):3d} calls  in {u['in']:,} out {u['out']:,}  ${u['cost']:.2f}")
