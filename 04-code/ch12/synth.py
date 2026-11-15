"""Chapter 12, real model run: generate 400 synthetic hardship cases from a persona x reason grid.

Usage: python3 synth.py run   (calls the API; caches out/synth_raw.jsonl, one line per grid cell)
       python3 synth.py       (summarises the cache)
Model: claude-haiku-4-5-20251001, default sampling settings, 40 calls of ten cases each.
"""
import json, sys, concurrent.futures as cf
from pathlib import Path
from policy import POLICY_TEXT

HERE = Path(__file__).resolve().parent
CACHE = HERE / "out/synth_raw.jsonl"
MODEL = "claude-haiku-4-5-20251001"
PERSONAS = [
    "an hourly warehouse worker in Phoenix, Arizona",
    "a self-employed food-truck owner in Albuquerque, New Mexico",
    "a retired school teacher on a pension in Las Vegas, Nevada",
    "a hospital nurse in Denver, Colorado",
    "a construction worker in Tucson, Arizona who writes in Spanish",
]
REASONS = ["job loss", "reduced hours", "medical bills", "divorce or separation",
           "a death in the family", "a wildfire or flood", "a business downturn", "an unexpected large expense"]

SCHEMA = """Return only a JSON array of 10 objects, no prose. Each object has exactly these keys:
 "message": the borrower's first message to Compass, Harbor Lending's chat assistant (1 to 4 sentences, in the borrower's own voice),
 "language": "en" or "es",
 "reason": short hardship reason,
 "income_type": one of "salaried", "hourly", "self_employed", "benefits", "none",
 "income_monthly": the monthly income in US dollars the borrower states in the message, or null if the message states none,
 "loans": list of the borrower's Harbor Lending loans, each {"last4": four digits as a string, "product": "auto" or "personal" or "small_business", "payments_behind": integer},
 "names_loan": true if the message says which loan the hardship concerns, else false,
 "prior_relief": null, or {"type": "deferral" or "extension", "months_ago": integer months since it ended},
 "expected_decision": the first-reply action the policy requires, one of ask_which_loan, ask_income, decline_window, refer_to_officer, draft_deferral."""


def prompt(persona, reason):
    return (f"You are writing test cases for an evaluation of a loan-servicing assistant.\n\n{POLICY_TEXT}\n\n"
            f"Write 10 realistic, varied hardship cases from {persona} whose hardship is {reason}. "
            f"Real borrowers differ: vary the details as they would.\n\n{SCHEMA}")


def call(cell):
    import anthropic
    persona, reason = cell
    msg = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=4000,
                                               messages=[{"role": "user", "content": prompt(persona, reason)}])
    return {"persona": persona, "reason_cell": reason, "text": msg.content[0].text, "model": msg.model,
            "in": msg.usage.input_tokens, "out": msg.usage.output_tokens}


def cells():
    return [(p, r) for p in PERSONAS for r in REASONS]


def load():
    return [json.loads(l) for l in open(CACHE)] if CACHE.exists() else []


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        done = {(r["persona"], r["reason_cell"]) for r in load()}
        todo = [c for c in cells() if c not in done]
        with cf.ThreadPoolExecutor(6) as ex, open(CACHE, "a") as f:
            for r in ex.map(call, todo):
                f.write(json.dumps(r) + "\n"); f.flush()
    rows = load()
    print(f"synthetic generation cached: {len(rows)} of {len(cells())} grid cells; model {rows[0]['model'] if rows else '-'}; "
          f"{sum(r['in'] for r in rows):,} input / {sum(r['out'] for r in rows):,} output tokens")
