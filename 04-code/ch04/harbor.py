"""Chapter 4 stand-ins. Harbor Lending and Compass are fictional.

Prices, run frequencies and people's rates are stated assumptions, labelled
as such in the chapter; change them to yours. The Compass components below
are small deterministic stand-ins with switchable defects, so the same
suite can be run against a clean build and against one defect per layer.
Seed 2026 throughout; nothing was tuned after a run.
"""
import heapq
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "truss"))
sys.path.insert(0, str(ROOT / "ch03"))
from truss.store import open_store  # noqa: E402

SEED = 2026
OUT = HERE / "out"
STORE = ROOT / "ch03" / "out" / "trace_store.db"

# Stated assumptions (illustrative).
PRICES = {"input_per_m": 3.00, "output_per_m": 15.00, "runner_per_min": 0.008}
OFFICER_RATE, LEAD_RATE = 60.0, 85.0            # dollars an hour, loaded (ledger)
RUNS_PER_MONTH = {"commit": 120, "pull_request": 35, "release": 2, "shadow": 0.5, "weekly": 4.33}
FLOWS = ["account_question", "fee_explanation", "statement_request",
         "payoff_letter", "lien_release", "hardship"]
SHARES = {"account_question": .415, "fee_explanation": .215, "statement_request": .143,
          "payoff_letter": .108, "lien_release": .060, "hardship": .059}
QUOTAS = {"hardship": 100, "fee_explanation": 70, "account_question": 40,
          "payoff_letter": 35, "lien_release": 30, "statement_request": 25}
TODAY = "2026-12-14"

# ---------------------------------------------------------------- policy corpus
CORPUS = [
    {"doc": "fee-schedule", "version": "fee-schedule-2026-03", "effective_from": "2026-03-01", "retired_on": None},
    {"doc": "fee-schedule", "version": "fee-schedule-2024-01", "effective_from": "2024-01-01", "retired_on": "2026-03-01"},
    {"doc": "hardship-policy", "version": "hardship-policy-2026-06", "effective_from": "2026-06-01", "retired_on": None},
    {"doc": "lien-release-guide", "version": "lien-release-guide-2026-02", "effective_from": "2026-02-01", "retired_on": None},
    {"doc": "payoff-procedures", "version": "payoff-procedures-2026-01", "effective_from": "2026-01-01", "retired_on": None},
    {"doc": "statement-guide", "version": "statement-guide-2025-11", "effective_from": "2025-11-01", "retired_on": None},
]
RETIRED = {d["version"] for d in CORPUS if d["retired_on"]}


def corpus(defects=()):
    """The folder retrieval indexes. Pilot state: the 2024 schedule still sits in it."""
    docs = [dict(d) for d in CORPUS]
    if "corpus_cleaned" in defects:
        docs = [d for d in docs if not d["retired_on"]]
    return docs


# ---------------------------------------------------------------- deterministic code (layer 1)
def fee_applies(days_late, grace_days=15, defects=()):
    """A late fee applies once the payment is more than grace_days late."""
    if "grace_off_by_one" in defects:
        return days_late >= grace_days
    return days_late > grace_days


def second_deferral_blocked(prior_deferral_on, today):
    """Hardship policy: no second deferral within twelve months of the first."""
    if not prior_deferral_on:
        return False
    y, m, d = map(int, prior_deferral_on.split("-"))
    ty, tm, td = map(int, today.split("-"))
    return (ty - y) * 12 + (tm - m) - (td < d) < 12


ROUTER_LABELS = set(FLOWS) | {"unknown"}


def parse_router(raw):
    """The wrapper around the router model: an unknown label goes to a person."""
    label = raw.strip().lower().replace(" ", "_")
    return label if label in FLOWS else "handoff"


def sms_parts(text, limit=160):
    return -(-len(text) // limit)


# ---------------------------------------------------------------- model components (layer 2)
TEMPLATES = {
    "account_question": ["what is my balance", "when is my next payment due", "how much do I still owe",
                         "is my autopay set up", "what's the interest rate on my loan"],
    "fee_explanation": ["why was I charged a late fee", "what is this $25 fee", "can you explain the fee on my statement",
                        "I paid late, is there a fee", "why is there an extra charge"],
    "statement_request": ["send me my october statement", "I need a copy of my statement", "can I get last month's statement"],
    "payoff_letter": ["I want to pay off my loan", "how much to pay it off", "send me a payoff letter"],
    "lien_release": ["when do I get my title", "I paid off my car where is the title", "lien release status"],
    "hardship": ["I lost my job and can't pay this month", "can I skip a payment", "I need to defer my payment",
                 "is there an extension I can get", "I'm having trouble making payments"],
}


def router_fixture(n=600, seed=SEED):
    """Labelled first messages, drawn to traffic shares (labels are the flow
    the message belongs to, as a careful reader would assign it)."""
    r = random.Random(f"router|{seed}")
    out = []
    for i in range(n):
        flow = r.choices(FLOWS, weights=[SHARES[f] for f in FLOWS])[0]
        out.append({"id": f"r{i:03d}", "text": r.choice(TEMPLATES[flow]), "label": flow})
    return out


def route_model(msg, defects=()):
    """Stand-in for the router model: right about 97% of the time, wrong at random otherwise."""
    text, mid = msg["text"], msg["id"]
    if "router_extension_fee" in defects and any(w in text for w in ("extension", "skip", "defer")):
        return "fee_explanation"     # the new prompt's examples mention an "extension fee"
    r = random.Random(f"route|{mid}")
    return msg["label"] if r.random() < 0.97 else r.choice(FLOWS)


def retrieval_fixture(n=120, seed=SEED):
    """Labelled policy queries with the document version a loan officer says is right."""
    r = random.Random(f"retr|{seed}")
    qs = [("what is the grace period before a late fee", "fee-schedule-2026-03"),
          ("how much is the late fee", "fee-schedule-2026-03"),
          ("is the fee waived for autopay", "fee-schedule-2026-03"),
          ("can a borrower get a second deferral", "hardship-policy-2026-06"),
          ("how long until the title is released", "lien-release-guide-2026-02"),
          ("what goes in a payoff letter", "payoff-procedures-2026-01"),
          ("how far back can statements be sent", "statement-guide-2025-11")]
    return [{"id": f"q{i:03d}", "query": q, "label": v} for i, (q, v) in
            ((i, r.choice(qs)) for i in range(n))]


def retrieve(q, docs, defects=()):
    """Stand-in retriever. With both fee schedules indexed, the 2024 one ranks
    first for grace-period wording about one time in three."""
    want = q["label"].rsplit("-", 2)[0]
    cands = [d for d in docs if d["doc"] == want]
    if len(cands) > 1 and "grace" in q["query"]:
        r = random.Random(f"rank|{q['id']}")
        return cands[1]["version"] if r.random() < 0.33 else cands[0]["version"]
    return cands[0]["version"]


# ---------------------------------------------------------------- conversations (layers 3 and 4)
def hardship_replay(trace_ids, defects=(), seed=SEED):
    """Replay recorded hardship conversations against a build. Returns per trace:
    did the reply draft an offer before income was confirmed? (planted at the
    Chapter 2 rate, 6 of 100; the income defect raises it to about 1 in 5)."""
    out = {}
    for t in trace_ids:
        r = random.Random(f"replay|{t}|{seed}")
        base = r.random() < 0.06
        early = base or ("offer_before_income" in defects and r.random() < 0.15)
        # a misrouting router sends 'skip', 'defer' and 'extension' openers (3 of 5) to the fee flow
        misrouted = "router_extension_fee" in defects and random.Random(f"msg|{t}").random() < 0.6
        out[t] = "fail" if early or misrouted else "pass"
    return out


PERSONAS = [("states income plainly", 0), ("gives an income range", 1), ("asks for a person", 0),
            ("has a prior deferral", 0)]


def simulate(scenario, defects=(), max_turns=30):
    """A scripted simulated borrower against a build. It answers each question
    the way its persona does, so a borrower who gives an income range repeats
    the range when asked again. Returns the turns used and whether the
    conversation reached an offer or a hand-off before the turn cap."""
    turns = 4                                   # greeting, verification, income question
    if "reask_on_range" in defects and scenario["range"]:
        while turns < max_turns:                # Compass re-asks; the borrower repeats the range
            turns += 2
    else:
        turns += scenario["extra_turns"]
    turns = min(turns, max_turns)
    return {"turns": turns, "resolved": turns < max_turns}


def scenarios(n=60, seed=SEED):
    r = random.Random(f"sim|{seed}")
    out = []
    for i in range(n):
        p, rng = PERSONAS[i % len(PERSONAS)]
        out.append({"id": f"s{i:02d}", "persona": p, "range": bool(rng), "extra_turns": r.randint(4, 10)})
    return out


def latency_p95(arrivals_per_min, minutes=60, workers=3, extra_retrieval_s=0.0, seed=SEED):
    """Queue simulation for one peak hour: reply turns arrive at random and wait
    for one of `workers` model slots. Service time is drawn around the pilot's
    mean chat-span latency, plus any extra seconds on retrieval turns."""
    r = random.Random(f"q|{seed}|{arrivals_per_min}|{extra_retrieval_s}")
    t, free, waits = 0.0, [0.0] * workers, []
    heapq.heapify(free)
    while t < minutes * 60:
        t += r.expovariate(arrivals_per_min / 60)
        service = r.lognormvariate(0.25, 0.5) + (extra_retrieval_s if r.random() < 0.27 else 0)
        start = max(t, heapq.heappop(free))
        heapq.heappush(free, start + service)
        waits.append(start + service - t)
    waits.sort()
    return waits[int(0.95 * len(waits))]


# ---------------------------------------------------------------- the pilot store (Chapter 3)
def dt(s):
    from datetime import datetime
    return datetime.fromisoformat(s[:19])


def store():
    if not STORE.exists():
        import build_store
        build_store.build()
    return open_store(STORE)


def truth():
    return json.load(open(ROOT / "ch03" / "out" / "truth.json"))


def tokens_by_flow(con):
    """Mean input and output tokens per conversation, from the chat spans."""
    q = ("SELECT t.flow, COUNT(DISTINCT t.trace_id), SUM(json_extract(s.attrs,'$.input_tokens')), "
         "SUM(json_extract(s.attrs,'$.output_tokens')), SUM(json_extract(s.attrs,'$.latency_ms')) "
         "FROM spans s JOIN traces t USING(trace_id) WHERE s.kind='chat' GROUP BY 1")
    return {f: {"conv": n, "in": i / n, "out": o / n, "latency_s": ms / n / 1000} for f, n, i, o, ms in con.execute(q)}


def conv_dollars(tok):
    return (tok["in"] * PRICES["input_per_m"] + tok["out"] * PRICES["output_per_m"]) / 1e6


def gate_sample(con):
    """The 300-trace stratified first-pass sample (same draw as Chapter 3)."""
    from truss import sampling as S
    frame = [{"trace_id": t, "flow": f} for t, f in con.execute("SELECT trace_id, flow FROM traces ORDER BY trace_id")]
    return [(t, w) for t, w in S.stratified(frame, "flow", QUOTAS, seed=SEED)], frame
