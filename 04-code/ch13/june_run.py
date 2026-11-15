"""Chapter 13: score the fresh June document set with the production configuration Chapter 11 left:
claude-haiku-4-5-20251001, extract-prompt-v1 for English documents and extract-prompt-v2 (the Spanish
glossary) for Spanish ones, payroll totals summed in code from the rows. REAL model calls; the key is
read from the environment by the SDK and never printed. Raw replies are cached to out/june-haiku.jsonl.
Victor's rule (Fri 14 May 2027): each critical field under 2% observed error and its one-sided 95% upper
bound under 5%.
Usage: python3 june_run.py run   (calls the model for uncached documents), then python3 june_run.py"""
import concurrent.futures as cf
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CH11 = HERE.parents[0] / "ch11"
sys.path.insert(0, str(CH11)); sys.path.insert(0, str(HERE.parents[0] / "truss"))
import extract as EX  # noqa: E402
import score as S  # noqa: E402
from specs import CRITICAL, APPLIES  # noqa: E402
from truss import fields as F  # noqa: E402
import june_docs as JD  # noqa: E402

RAW = HERE / "out" / "june-haiku.jsonl"
GLOSS = ("\n\nSpanish documents: 'Quincenal' means semimonthly (twice a month), 'Catorcenal' means biweekly "
         "(every two weeks), 'Mensual' means monthly, 'Semanal' means weekly. Dates written as 05/06/2027 in a Spanish "
         "document are day first (5 June 2027).")


def prompt(d):
    if d["lang"] == "es":
        return "extract-prompt-v2", EX.PROMPT.replace("\n\nDocument:\n<<<", GLOSS + "\n\nDocument:\n<<<").format(text=d["text"])
    return "extract-prompt-v1", EX.PROMPT.format(text=d["text"])


def call(d):
    import anthropic
    pv, p = prompt(d)
    msg = anthropic.Anthropic().messages.create(model=EX.MODELS["haiku"], max_tokens=1500, messages=[{"role": "user", "content": p}])
    return {"id": d["id"], "model": EX.MODELS["haiku"], "prompt": pv, "raw": msg.content[0].text,
            "in_tok": msg.usage.input_tokens, "out_tok": msg.usage.output_tokens}


def cached():
    return {j["id"]: j for j in map(json.loads, RAW.read_text().splitlines())} if RAW.exists() else {}


if __name__ == "__main__":
    docs = JD.load()
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        done = cached(); todo = [d for d in docs if d["id"] not in done]
        with cf.ThreadPoolExecutor(6) as ex, RAW.open("a") as fh:
            for r in ex.map(call, todo):
                fh.write(json.dumps(r, ensure_ascii=False) + "\n"); fh.flush()
    C = cached()
    print(f"== June set: {len(docs)} documents; {len(C)} replies cached from {EX.MODELS['haiku']} "
          f"({sum(c['in_tok'] for c in C.values()):,} input / {s1 if (s1 := sum(c['out_tok'] for c in C.values())) else 0:,} output tokens); "
          f"prompts {dict((p, sum(c['prompt'] == p for c in C.values())) for p in ('extract-prompt-v1', 'extract-prompt-v2'))}")
    fixed, unparsed = {}, []
    for d in docs:
        obj, _ = F.parse_json(C[d["id"]]["raw"])
        if obj is None:
            unparsed.append(d["id"]); obj = {}
        o = dict(obj)
        if d["gold"]["doc_type"] == "bank_statement" or o.get("doc_type") == "bank_statement":
            o["payroll_total"] = round(sum(F.money(r["amount"]) for r in o.get("payroll_deposits") or []), 2)
        fixed[d["id"]] = {"obj": o}
    oc = S.outcomes(docs, fixed)
    T = F.field_table((f, o) for fo in oc.values() for f, o in fo.items())
    print(f"  replies that did not parse after fence repair: {len(unparsed)} {unparsed}")
    res = []
    print("  Victor's rule, critical fields:")
    for f in CRITICAL:
        t = T[f]; n = t["present"] + t["invented"]; k = t["errors_where_present"] + t["invented"]
        ub = F.upper_one_sided(k, n) if n else 1.0; ok = n > 0 and k / n < 0.02 and ub < 0.05
        res.append({"field": f, "n": n, "errors": k, "rate": k / n if n else None, "upper": ub, "pass": ok})
        print(f"    {f:<22} {k:>2}/{n:<3} {k / n if n else 0:6.1%}  upper {ub:6.1%}  {'PASS' if ok else 'FAIL'}")
    errs = [(d["id"], d["lang"], d["quality"], f, fixed[d["id"]]["obj"].get(f), d["gold"][f]) for d in docs for f in CRITICAL
            if oc[d["id"]][f] not in ("tp", "tn")]
    for e in errs:
        print(f"    error {e[0]} {e[1]} {e[2]:<5} {e[3]:<22} got {e[4]!r} gold {e[5]!r}")
    flips = [d["id"] for d in docs if S.decision(d["gold"], d) != S.decision(fixed[d["id"]]["obj"], d)]
    allr = sum(all(v in ("tp", "tn") for v in oc[d["id"]].values()) for d in docs)
    print(f"  documents with every field right {allr}/{len(docs)}; hardship decisions changed {len(flips)} {flips}")
    json.dump({"n": len(docs), "victor": res, "errors": errs, "flips": flips, "all_right": allr, "unparsed": unparsed,
               "tokens": [sum(c['in_tok'] for c in C.values()), sum(c['out_tok'] for c in C.values())]},
              open(HERE / "out" / "june.json", "w"), indent=1, default=str)
