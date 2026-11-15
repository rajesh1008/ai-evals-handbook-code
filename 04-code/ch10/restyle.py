"""Chapter 10, real model run: the same 200 replies in a candidate release's longer style.
A small fast model rewrites each reply about 50% longer, keeping every fact and the decision;
extract.py checks that no decision changed. Model: claude-haiku-4-5-20251001, 1 November 2026.
Usage: python3 restyle.py run   (calls the API, caches out/restyled.jsonl)
"""
import json, sys, concurrent.futures as cf
from pathlib import Path
import fee200 as F, replies as RP

HERE = Path(__file__).resolve().parent
RAW = HERE / "out" / "restyled.jsonl"
PROMPT = """Rewrite this reply from a loan-servicing chat assistant so it is about {target} words, roughly half as long again.
Add a sentence on how late fees and the grace period work in general and a closing offer of further help.
Keep every fact, amount, loan number and the decision exactly as they are. Do not add any new amount, date or fee status.
Write only the rewritten reply.

Reply:
{reply}"""


def call(item):
    import anthropic
    tid, reply = item
    target = int(len(reply.split()) * 1.5)
    msg = anthropic.Anthropic().messages.create(model=RP.MODEL, max_tokens=800,
                                                 messages=[{"role": "user", "content": PROMPT.format(target=target, reply=reply)}])
    return {"trace_id": tid, "reply": msg.content[0].text.strip(), "model": msg.model,
            "in_tok": msg.usage.input_tokens, "out_tok": msg.usage.output_tokens}


def load():
    return {j["trace_id"]: j for j in map(json.loads, RAW.read_text().splitlines())}


if __name__ == "__main__":
    base = RP.load()
    if sys.argv[1:] == ["run"]:
        done = load() if RAW.exists() else {}
        todo = [(k, v["reply"]) for k, v in base.items() if k not in done]
        with cf.ThreadPoolExecutor(8) as ex, RAW.open("a") as fh:
            for res in ex.map(call, todo):
                fh.write(json.dumps(res) + "\n")
    got = load()
    w0 = sum(len(base[k]["reply"].split()) for k in got) / len(got)
    w1 = sum(len(v["reply"].split()) for v in got.values()) / len(got)
    print(f"restyled {len(got)}; mean words {w0:.0f} -> {w1:.0f}; tokens in "
          f"{sum(v['in_tok'] for v in got.values()):,} out {sum(v['out_tok'] for v in got.values()):,}")
