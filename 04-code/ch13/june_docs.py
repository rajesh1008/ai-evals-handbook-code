"""Chapter 13: the fresh June 2027 document set Chapter 11 asked for (fixture).

160 documents (70 pay stubs, 50 bank statements, 40 hardship letters) from Chapter 11's 30 layouts,
with a new seed (2027) and the generator's four literal dates one calendar month later than Chapter 11's,
so pay periods end in May and June and letters are dated in June. Uploads: Tue 1 June to Thu 1 July 2027 (a June pay period that ends on the 30th is uploaded in July).
Document IDs hd-0201 to hd-0360. The gold record is exact (filled from the values); in the story it is
the officers' re-keyed values, which they type for every upload until the re-keying rule is lifted.
Usage: python3 june_docs.py   (writes out/june_docs.jsonl)"""
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
CH11 = HERE.parents[0] / "ch11"
sys.path.insert(0, str(CH11)); sys.path.insert(0, str(HERE.parents[0] / "truss"))

OUT = HERE / "out" / "june_docs.jsonl"
SEED = 2027
N = {"pay_stub": 70, "bank_statement": 50, "hardship_letter": 40}


SHIFTS = [("date(2027, 4, 1) + timedelta", "date(2027, 5, 1) + timedelta"),   # pay stub period ends: May 1 to Jun 10
          ("month = rng.choice([3, 4])", "month = rng.choice([4, 5])"),        # statements for April or May
          ("date(2027, rng.choice([1, 2, 3, 4])", "date(2027, rng.choice([2, 3, 4, 5])"),  # hardship began
          ("ldate = date(2027, 5, rng", "ldate = date(2027, 6, rng")]          # letters dated in June


def _generator():
    """Chapter 11's generator with its four literal dates moved one month later (asserted present)."""
    import types
    src = (CH11 / "docs.py").read_text()
    for a, b in SHIFTS:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    mod = types.ModuleType("docs_june"); mod.__file__ = str(CH11 / "docs.py")
    exec(compile(src, "docs_june", "exec"), mod.__dict__)
    return mod


def build():
    G = _generator()
    if True:
        rng = random.Random(SEED)
        docs = []
        for kind, fn in [("pay_stub", G.make_stub), ("bank_statement", G.make_statement), ("hardship_letter", G.make_letter)]:
            for i in range(N[kind]):
                lay, lang, text, gold, traps, extra = fn(rng, i)
                quality = "photo" if rng.random() < 0.25 else "clean"
                if quality == "photo":
                    text = G.photograph(text, rng, 0.04)
                docs.append({"layout": lay, "lang": lang, "quality": quality, "text": text, "gold": gold, "traps": traps, "extra": extra})
    rng.shuffle(docs)
    bdays = [date(2027, 6, 1) + timedelta(days=k) for k in range(30)]
    bdays = [d for d in bdays if d.weekday() < 5]
    for j, d in enumerate(docs):
        d["id"] = f"hd-{201 + j:04d}"
        up = bdays[j * len(bdays) // len(docs)]
        pe = date.fromisoformat(d["gold"]["period_end"])
        while up <= pe or up.weekday() > 4:
            up += timedelta(days=1)
        assert up <= date(2027, 7, 2), (d["id"], pe)
        d["uploaded"] = up.isoformat()
        d["payment"] = round(rng.uniform(240, 720), 2)
    return docs


def load():
    return [json.loads(x) for x in OUT.read_text().splitlines()]


if __name__ == "__main__":
    docs = build()
    OUT.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in docs))
    from collections import Counter
    print("documents:", len(docs), dict(Counter(d["gold"]["doc_type"] for d in docs)), docs[0]["id"], "to", docs[-1]["id"])
    print("languages:", dict(Counter(d["lang"] for d in docs)), "quality:", dict(Counter(d["quality"] for d in docs)))
    print("traps:", dict(Counter(t for d in docs for t in d["traps"])))
    print("period ends:", min(d["gold"]["period_end"] for d in docs), "to", max(d["gold"]["period_end"] for d in docs),
          "; uploads:", min(d["uploaded"] for d in docs), "to", max(d["uploaded"] for d in docs))
