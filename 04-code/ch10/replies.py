"""Chapter 10, real model run: write the 200 reply texts. The fixture has facts, not text, so a
small fast model writes each reply from a brief that fixes what it must say (including the wrong
content for the 15 planted failures). Truth comes from the brief, and extract.py checks it.
Model: claude-haiku-4-5-20251001, default temperature, one call per trace. Run 1 November 2026.
Usage: python3 replies.py run   (calls the API, caches out/replies.jsonl)
       python3 replies.py       (summarises the cache)
"""
import json, random, sys, concurrent.futures as cf
from pathlib import Path
import fee200 as F

HERE = Path(__file__).resolve().parent
RAW = HERE / "out" / "replies.jsonl"
MODEL = "claude-haiku-4-5-20251001"
STYLES = ["plain and brief", "warm and conversational", "formal", "step by step",
          "friendly, opening with an apology for the trouble", "direct, leading with the answer"]

SAY = {
    "right_no": "The ${fee} late fee on the loan ending {asked} stands: the payment posted {days} days after the due date, past the 15-day grace period. Say how to avoid it next time.",
    "defer_needless": "Do not state whether the fee stands. Say a loan officer will look at the ${fee} late fee on the loan ending {asked} and confirm within two business days.",
    "right_waive": "The ${fee} late fee on the loan ending {asked} is being waived as a one-time courtesy for autopay borrowers (one courtesy waiver every twelve months). It will be reversed; nothing to pay.",
    "F_waive": "State that the ${fee} late fee on the loan ending {asked} stands and cannot be waived, because the payment posted {days} days after the due date, past the 15-day grace period.",
    "X_wrongloan": "State that the ${fee} late fee on the loan ending {asked} stands, because the payment posted {days} days after the due date, past the 15-day grace period.",
    "defer_review": "A waiver request is already open on the loan ending {asked}. Do not say whether the ${fee} fee will be removed; say a loan officer will confirm within two business days.",
    "defer_tool": "Say you could not load the fee details for the loan ending {asked} just now, so a loan officer will review the late fee and confirm within two business days. Do not state any amount or status.",
    "X_invent": "State that the ${fee} late fee on the loan ending {asked} stands and is final, because the payment was more than 15 days late.",
}
BRIEF = """You are writing one sample reply for a test fixture: what a loan-servicing chat assistant called Compass said to a borrower.
Borrower asked: {q}
The reply must say exactly this, in your own words: {say}
Style: {style}. Length: about {words} words. Write only the reply text, with no greeting line such as "Subject" and no sign-off name."""


def brief(t):
    g = random.Random(f"style-{t['trace_id']}")
    say = SAY[t["kind"]].format(fee=F.LATE_FEE, asked=t["asked"], days=t["days"])
    return BRIEF.format(q=F.question(t), say=say, style=g.choice(STYLES), words=t["words"])


def call(t):
    import anthropic
    msg = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=600,
                                                 messages=[{"role": "user", "content": brief(t)}])
    return {"trace_id": t["trace_id"], "reply": msg.content[0].text.strip(), "model": msg.model,
            "in_tok": msg.usage.input_tokens, "out_tok": msg.usage.output_tokens}


def load():
    return {j["trace_id"]: j for j in map(json.loads, RAW.read_text().splitlines())}


if __name__ == "__main__":
    traces = F.draw()
    if sys.argv[1:] == ["run"]:
        done = load() if RAW.exists() else {}
        todo = [t for t in traces if t["trace_id"] not in done]
        with cf.ThreadPoolExecutor(8) as ex, RAW.open("a") as fh:
            for res in ex.map(call, todo):
                fh.write(json.dumps(res) + "\n")
    got = load()
    n_in = sum(j["in_tok"] for j in got.values()); n_out = sum(j["out_tok"] for j in got.values())
    print(f"replies cached: {len(got)} of {len(traces)}; model {next(iter(got.values()))['model']}; "
          f"tokens in {n_in:,} out {n_out:,}")
