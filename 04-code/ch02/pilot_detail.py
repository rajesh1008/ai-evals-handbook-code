"""Chapter 2 fixture: what the Lab needs beyond the Chapter 1 trace table.

Harbor Lending and Compass are fictional. This module derives, from seed 2026:
  * the tool calls recorded on every pilot trace (by flow; hardship traces
    that reached an offer also call draft_offer);
  * the first-pass labels for the 300-trace stratified sample. The per-flow
    failure counts were fixed when the book was planned (273 of 300 pass,
    no wrong hardship offer); WHICH traces fail, and with which note, is
    drawn from the seed;
  * a short rendering of each sampled conversation for the labeller CLI.
Nothing here was tuned after a run.
"""
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss.complete import REQUIRED_TOOLS  # noqa: E402
from truss.sample import stratified_sample  # noqa: E402
from truss.store import open_store  # noqa: E402

SEED = 2026
QUOTAS = {"hardship": 100, "fee_explanation": 70, "account_question": 40,
          "payoff_letter": 35, "lien_release": 30, "statement_request": 25}
ORDER = ["account_question", "fee_explanation", "statement_request",
         "payoff_letter", "lien_release", "hardship"]
EXTRA_TOOLS = {"statement_request": [], "payoff_letter": ["send_letter"],
               "lien_release": [], "fee_explanation": [], "account_question": []}

# First-pass failure notes and how many sampled traces carry each (planned).
FAILURES = {
    "hardship": [("offer drafted before income confirmed", 6),
                 ("no hand-off when borrower asked for a person", 3),
                 ("offer sent without saying a loan officer must approve it", 2)],
    "fee_explanation": [("ten-day grace period quoted (policy is 15)", 4),
                        ("fee not waived when policy says waive", 2)],
    "account_question": [("wrong balance date", 2), ("missed borrower's second loan", 1)],
    "payoff_letter": [("per diem interest omitted", 2), ("wrong good-through date", 1)],
    "lien_release": [("release promised before title office date", 2),
                     ("wrong title state", 1)],
    "statement_request": [("wrong statement period", 1)],
}
ANNOTATOR = {"hardship": "Grace Holloway", "fee_explanation": "evaluation lead",
             "lien_release": "evaluation lead", "account_question": "Ryan Mitchell",
             "statement_request": "Ryan Mitchell", "payoff_letter": "Ryan Mitchell"}

LINES = {
    "account_question": ("What's my balance on the car loan?",
                         "Your balance on loan ending 4471 is $14,382.10 as of today."),
    "fee_explanation": ("Why was I charged a $25 late fee?",
                        "Your payment posted 11 days after the due date. Harbor Lending's grace period is 15 days, so this fee should not apply; I've asked a colleague to reverse it."),
    "statement_request": ("Can you send me my September statement?",
                          "I've sent your September 2026 statement to the email on file."),
    "payoff_letter": ("I need a payoff letter for my truck loan.",
                      "Your payoff is $9,804.55, good through 30 October 2026, plus $2.71 per day after that. The letter is on its way."),
    "lien_release": ("When will the lien on my car be released?",
                     "Your loan is paid in full. Arizona's title office usually records the release within ten business days."),
    "hardship": ("I lost hours at work and can't make this month's payment.",
                 "I'm sorry to hear that. Can you tell me your current monthly income? Then I can check what options you have."),
}


FAIL_LINES = {
    "offer drafted before income confirmed":
        "I can offer you a three-month deferral. I've sent it to a loan officer to finalise.",
    "ten-day grace period quoted (policy is 15)":
        "Payments more than 10 days late incur a $25 fee, so the fee applies.",
}


def tools_for(trace_id, flow, reached_offer):
    tools = list(REQUIRED_TOOLS[flow]) + EXTRA_TOOLS.get(flow, [])
    if flow == "hardship":
        tools += ["check_hardship_eligibility"] + (["draft_offer"] if reached_offer else [])
    return tools


def reached_offer(trace_id):
    return random.Random(f"offer|{trace_id}").random() < 0.64


def first_pass_sample(db=None):
    db = db or open_store()
    return stratified_sample(db, QUOTAS, SEED)


def first_pass_labels(db=None):
    """The labels the first pass produced, one row per sampled trace."""
    db = db or open_store()
    sample = first_pass_sample(db)
    flows = dict(db.execute(
        f"SELECT trace_id, flow FROM traces WHERE trace_id IN ({','.join('?' * len(sample))})", sample))
    rng = random.Random(SEED)
    rows = {}
    for flow in QUOTAS:
        ids = sorted(t for t in sample if flows[t] == flow)
        notes = [note for note, k in FAILURES[flow] for _ in range(k)]
        if flow == "hardship":  # offer-related notes can only land on traces with an offer
            offer_notes = [n for n in notes if "offer" in n]
            with_offer = [t for t in ids if reached_offer(t)]
            first = rng.sample(with_offer, len(offer_notes))
            rest = rng.sample([t for t in ids if t not in first], len(notes) - len(offer_notes))
            failing, notes = first + rest, offer_notes + [n for n in notes if "offer" not in n]
        else:
            failing = rng.sample(ids, len(notes))
        for t in ids:
            rows[t] = {"trace_id": t, "flow": flow, "verdict": "pass", "note": "",
                       "annotator": ANNOTATOR[flow]}
        for t, note in zip(failing, notes):
            rows[t].update(verdict="fail", note=note)
    return [rows[t] for t in sample]


def trace_view(db, trace_id, drop_tools=False, note=""):
    flow, turns = db.execute("SELECT flow, turns FROM traces WHERE trace_id = ?",
                             (trace_id,)).fetchone()
    offer = flow == "hardship" and reached_offer(trace_id)
    tools = [] if drop_tools else tools_for(trace_id, flow, offer)
    b, c = LINES[flow]
    c = FAIL_LINES.get(note, c)
    return {"trace_id": trace_id, "flow": flow, "turns": turns, "tools": tools,
            "reached_offer": offer, "messages": [("borrower", b), ("Compass", c)]}
