"""Chapter 11, Try It Yourself: three variations on the lab.
  1. Take the payroll total from the extracted rows instead of the model's own sum.
  2. Rerun the Spanish documents with prompt v2 (a glossary for frequency words and day-first dates).
     Real run, claude-haiku-4-5-20251001, cached to out/extract-haiku-v2-es.jsonl.
  3. How many documents a zero-error field needs before it can pass Victor's threshold.
Usage: python3 try_its.py [run]
"""
import json, sys, concurrent.futures as cf
import docs as DOCS, extract as EX, score as S
from truss import fields as F
from specs import BY

docs = DOCS.load(); D = {d["id"]: d for d in docs}
H = S.parsed("haiku")

print("== 1. payroll total from its own rows")
before = sum(S.outcomes([d], H)[d["id"]]["payroll_total"] == "tp" for d in docs if d["gold"]["doc_type"] == "bank_statement")
after = 0
for d in docs:
    if d["gold"]["doc_type"] != "bank_statement":
        continue
    rows = H[d["id"]]["obj"].get("payroll_deposits") or []
    total = round(sum(F.money(r["amount"]) for r in rows), 2)
    after += F.outcome(BY["payroll_total"], total, d["gold"]["payroll_total"]) == "tp"
print(f"  payroll_total right: model's sum {before}/60, sum of its rows {after}/60")

print("== 2. Spanish documents with prompt v2")
GLOSS = ("\n\nSpanish documents: 'Quincenal' means semimonthly (twice a month), 'Catorcenal' means biweekly "
         "(every 14 days), 'Mensual' monthly, 'Semanal' weekly. Spanish numeric dates are day first: 04/05/2027 "
         "is 4 May 2027.")
PATH = EX.HERE / "out" / "extract-haiku-v2-es.jsonl"
es = [d for d in docs if d["lang"] == "es"]


def call(d):
    import anthropic
    msg = anthropic.Anthropic().messages.create(model=EX.MODELS["haiku"], max_tokens=1500, messages=[
        {"role": "user", "content": EX.PROMPT.replace("\n\nDocument:\n<<<", GLOSS + "\n\nDocument:\n<<<").format(text=d["text"])}])
    return {"id": d["id"], "model": EX.MODELS["haiku"], "prompt": "extract-prompt-v2", "raw": msg.content[0].text}


if len(sys.argv) > 1 and sys.argv[1] == "run" and not PATH.exists():
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(call, es))
    PATH.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res))
if PATH.exists():
    v2 = {}
    for line in PATH.read_text().splitlines():
        r = json.loads(line); v2[r["id"]] = {"obj": F.parse_json(r["raw"])[0]}
    o1, o2 = S.outcomes(es, H), S.outcomes(es, v2)
    for f in ("pay_frequency", "period_end", "employer", "person_name"):
        e1 = sum(o1[d["id"]][f] in ("wrong", "miss", "invented") for d in es)
        e2 = sum(o2[d["id"]][f] in ("wrong", "miss", "invented") for d in es)
        print(f"  {f:<16} errors on {len(es)} Spanish documents: v1 {e1}, v2 {e2}")
    allf = lambda o: sum(v in ("wrong", "miss", "invented") for d in es for v in o[d["id"]].values())
    print(f"  all fields: v1 {allf(o1)} errors, v2 {allf(o2)} errors")

print("== 3. documents needed for a zero-error field to pass (one-sided 95% upper bound under 5%)")
n = 1
while F.upper_one_sided(0, n) >= 0.05:
    n += 1
print(f"  zero errors in {n} documents; with one error: ", end="")
m = 1
while not (1 / m < 0.02 and F.upper_one_sided(1, m) < 0.05):
    m += 1
print(f"{m} documents; with two errors: ", end="")
k = 1
while not (2 / k < 0.02 and F.upper_one_sided(2, k) < 0.05):
    k += 1
print(f"{k} documents")
