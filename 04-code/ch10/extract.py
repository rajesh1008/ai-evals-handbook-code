"""Chapter 10: fact extraction for partial credit, by a fixed pattern and by a model.
What each reply claims: status (stands, waived, officer, none), amount in dollars, loan last four.
The model run is real: claude-haiku-4-5-20251001, 1 November 2026, one call per reply, cached.
Usage: python3 extract.py run   (calls the API for the base and restyled replies)
"""
import json, re, sys, concurrent.futures as cf
from pathlib import Path
import fee200 as F, replies as RP

HERE = Path(__file__).resolve().parent
RAW = HERE / "out" / "extract.jsonl"
CLAIMED = {"right_no": "stands", "defer_needless": "officer", "right_waive": "waived", "F_waive": "stands",
           "X_wrongloan": "stands", "defer_review": "officer", "defer_tool": "officer", "X_invent": "stands"}
RIGHT_STATUS = {"stands": "stands", "waive": "waived", "officer": "officer", "officer_tool": "officer"}
PROMPT = """Read this reply from a loan-servicing assistant about a late fee and report what it tells the borrower.
Reply:
{reply}
Answer with one JSON object and nothing else: {{"status": one of "stands" (the fee is owed), "waived" (the fee is removed or reversed), "officer" (a person will decide later), "none" (no status given); "amount": the fee amount in dollars as a number, or null; "loan": the last four digits of the loan named, or null}}"""


def regex(reply):
    low = reply.lower()
    if re.search(r"loan officer|officer will", low):
        status = "officer"
    elif re.search(r"\b(waived?|waiving|reversed?|removed?|credited)\b", low):
        status = "waived"
    elif re.search(r"\b(stands|applies|valid|correct|owed|still due)\b", low):
        status = "stands"
    else:
        status = "none"
    amt = re.search(r"\$(\d+)(?:\.\d\d)?", reply)
    loan = re.search(r"ending(?: in)? (\d{4})", reply)
    return {"status": status, "amount": int(amt.group(1)) if amt else None, "loan": loan.group(1) if loan else None}


def call(item):
    import anthropic
    key, reply = item
    msg = anthropic.Anthropic().messages.create(model=RP.MODEL, max_tokens=120,
                                                 messages=[{"role": "user", "content": PROMPT.format(reply=reply)}])
    text = msg.content[0].text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    try:
        got = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        got = {}
    if got.get("amount") is not None:
        got["amount"] = int(float(got["amount"]))
    if got.get("loan") is not None:
        got["loan"] = str(got["loan"])
    return {"key": key, **{k: got.get(k) for k in ("status", "amount", "loan")}, "raw": text,
            "in_tok": msg.usage.input_tokens, "out_tok": msg.usage.output_tokens}


def load():
    return {j["key"]: j for j in map(json.loads, RAW.read_text().splitlines())} if RAW.exists() else {}


if __name__ == "__main__":
    import restyle as RS
    if sys.argv[1:] == ["run"]:
        items = [(f"base:{k}", v["reply"]) for k, v in RP.load().items()]
        items += [(f"restyled:{k}", v["reply"]) for k, v in RS.load().items()]
        done = load()
        todo = [i for i in items if i[0] not in done]
        with cf.ThreadPoolExecutor(8) as ex, RAW.open("a") as fh:
            for res in ex.map(call, todo):
                fh.write(json.dumps(res) + "\n")
    print(f"extractions cached: {len(load())}")
