"""Modest REAL Anthropic fidelity judgements on simulated vs real turn snippets.

Usage:
  python3 real_sim.py          # use cache if present
  python3 real_sim.py --live   # call Anthropic (needs ANTHROPIC_API_KEY)
Never prints the API key.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

OUT = Path(__file__).parent / "out"
CACHE = OUT / "real_sim.json"
MODEL = "claude-haiku-4-5-20251001"
N = 24  # modest sample

SNIPPETS = [
    ("sim", "User: I need a deferral because hours were cut. Assistant: I can offer two months. User: OK thanks."),
    ("sim", "User: My pay stub shows overtime dropped. Assistant: Please upload the stub. User: Done."),
    ("real", "User: Hold on, that grace period sounds wrong. Assistant: Let me recompute. User: The fee was thirty last year."),
    ("real", "User: No, I already sent the hardship packet last Tuesday. Assistant: I don't see it. User: Check the portal again."),
    ("sim", "User: Extension please. Assistant: Approved for thirty days. User: Great."),
    ("real", "User: Why are you asking for YTD again? I gave it. Assistant: Policy requires it. User: Fine, but this is the third time."),
    ("sim", "User: Can I skip a payment? Assistant: A deferral may apply. User: Whatever you think."),
    ("real", "User: That offer is less than Diane explained last month. Assistant: Let me open the bulletin. User: HB-2027-12."),
    ("sim", "User: Payment plan. Assistant: Three equal instalments. User: OK."),
    ("real", "User: Stop. You just quoted the retired schedule. Assistant: Checking index. User: Fee schedule 2026-03."),
    ("sim", "User: Refer me to an officer. Assistant: Connecting you. User: Thanks."),
    ("real", "User: I'm not agreeing until you confirm the anniversary rule. Assistant: Within twelve months. User: Outside, Victor said."),
    ("sim", "User: Hardship packet. Assistant: Forms sent. User: Got them."),
    ("real", "User: Your last message ignored the Spanish stub. Assistant: Re-reading. User: Net is take-home."),
    ("sim", "User: Hours cut at Desert Ridge. Assistant: Qualifies. User: Proceed."),
    ("real", "User: Don't draft yet — eligibility failed last week. Assistant: Re-running checks. User: Good."),
    ("sim", "User: Two month deferral. Assistant: Done. User: Perfect."),
    ("real", "User: Push back: stated work is not unemployment. Assistant: Correcting label. User: Keep going."),
    ("sim", "User: Need help. Assistant: Hardship options. User: Deferral is fine."),
    ("real", "User: I will not accept a wrong offer again. Assistant: Reading MC-01. User: Bound under 0.5%."),
    ("sim", "User: Plan please. Assistant: Drafted. User: Submit."),
    ("real", "User: Clarify the tool you called. Assistant: get_loan. User: Wrong loan_id last time."),
    ("sim", "User: Extension. Assistant: Thirty days. User: Thanks so much!"),
    ("real", "User: That answer is incomplete. Ask me about dependents. Assistant: How many? User: Two."),
]

PROMPT = """You are scoring whether a short hardship-chat snippet looks like a cooperative simulator or a pushback-heavy real borrower.
Reply with JSON only: {"label":"simulator"|"realish","pushback":true|false,"confidence":0-1}
Snippet:
"""

def call_anthropic(text: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()  # reads env
    msg = client.messages.create(
        model=MODEL,
        max_tokens=120,
        messages=[{"role": "user", "content": PROMPT + text}],
    )
    raw = msg.content[0].text.strip()
    # extract JSON
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        return json.loads(raw[start:end+1])
    return {"label": "unknown", "pushback": False, "confidence": 0.0, "raw": raw}

def main():
    live = "--live" in sys.argv
    if CACHE.exists() and not live:
        print(json.dumps(json.loads(CACHE.read_text()), indent=2)[:1500])
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("No ANTHROPIC_API_KEY; write pending stub")
        CACHE.write_text(json.dumps({"status": "pending", "n": 0}))
        return
    rows = []
    usage = {"in": 0, "out": 0}
    for kind, snip in SNIPPETS[:N]:
        try:
            j = call_anthropic(snip)
        except TypeError:
            # older SDK quirks
            j = call_anthropic(snip)
        j["true_kind"] = kind
        j["snippet"] = snip[:80]
        rows.append(j)
        time.sleep(0.15)
    # agreement with true_kind
    correct = 0
    for r in rows:
        pred = r.get("label")
        if pred == "simulator" and r["true_kind"] == "sim":
            correct += 1
        elif pred == "realish" and r["true_kind"] == "real":
            correct += 1
    out = {
        "status": "ok",
        "model": MODEL,
        "n": len(rows),
        "correct": correct,
        "accuracy": correct / len(rows) if rows else None,
        "pushback_flagged": sum(1 for r in rows if r.get("pushback")),
        "rows": rows,
    }
    CACHE.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in out if k != "rows"}, indent=2))

if __name__ == "__main__":
    main()
