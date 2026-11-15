"""Chapter 11: generated queries for Compass's account lookups, scored three ways.

Compass answers "when was my last payment" by writing SQL against a read-only accounts view.
Thirty lookup questions, each with a gold query written by Ben Fletcher's team. A real model
(claude-haiku-4-5-20251001, cached) writes the SQL. Each generated query is scored by
  (1) normalised string match with the gold query,
  (2) execution match on the development database (dev.db: one loan each, no gaps, no ties),
  (3) execution match on a database built to tell queries apart (probe.db: second loans,
      missed payments, waived fees, deferrals, same-day ties, closed loans).
Results are compared as multisets of rows, money rounded to the cent. Seed 2026. Today is 2027-05-20.
Usage: python3 sql_lab.py run   (needs ANTHROPIC_API_KEY)   |   python3 sql_lab.py   (scores the cache)
"""
import json, random, re, sqlite3, sys, concurrent.futures as cf
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
MODEL = "claude-haiku-4-5-20251001"
SCHEMA = """CREATE TABLE borrowers (borrower_id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE loans (loan_id INTEGER PRIMARY KEY, borrower_id INTEGER, product TEXT, last4 TEXT, opened DATE, balance REAL, status TEXT);
CREATE TABLE payments (payment_id INTEGER PRIMARY KEY, loan_id INTEGER, due_date DATE, paid_date DATE, amount REAL);
CREATE TABLE fees (fee_id INTEGER PRIMARY KEY, loan_id INTEGER, charged DATE, kind TEXT, amount REAL, waived INTEGER);
CREATE TABLE deferrals (deferral_id INTEGER PRIMARY KEY, loan_id INTEGER, start_date DATE, months INTEGER);"""
NOTES = """Notes: product is 'auto' or 'personal'. status is 'open' or 'closed'. paid_date is NULL for a payment not yet made; amount is the amount due, and the amount paid when paid_date is set. waived is 1 for a waived fee, else 0. kind is 'late' or 'nsf'. A deferral covers start_date through start_date plus months. Dates are ISO strings. Today is 2027-05-20."""

B = 1007
Q = [
 ("How many loans does borrower 1007 have?", f"SELECT COUNT(*) FROM loans WHERE borrower_id={B}"),
 ("How many open loans does borrower 1007 have?", f"SELECT COUNT(*) FROM loans WHERE borrower_id={B} AND status='open'"),
 ("What is the total outstanding balance on borrower 1007's open loans?", f"SELECT ROUND(SUM(balance),2) FROM loans WHERE borrower_id={B} AND status='open'"),
 ("What are the last four digits of borrower 1007's auto loan?", f"SELECT last4 FROM loans WHERE borrower_id={B} AND product='auto'"),
 ("When was borrower 1007's auto loan opened?", f"SELECT opened FROM loans WHERE borrower_id={B} AND product='auto'"),
 ("On what date did borrower 1007 last make a payment?", f"SELECT MAX(p.paid_date) FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B}"),
 ("How much was borrower 1007's most recent payment? If several were made that day, give the total paid that day.",
  f"SELECT ROUND(SUM(p.amount),2) FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND p.paid_date=(SELECT MAX(p2.paid_date) FROM payments p2 JOIN loans l2 USING(loan_id) WHERE l2.borrower_id={B})"),
 ("How much has borrower 1007 paid in total since 1 January 2027?", f"SELECT ROUND(SUM(p.amount),2) FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND p.paid_date>='2027-01-01'"),
 ("How much did borrower 1007 pay in April 2027?", f"SELECT ROUND(SUM(p.amount),2) FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND p.paid_date BETWEEN '2027-04-01' AND '2027-04-30'"),
 ("How many payments has borrower 1007 missed (due before today and not paid)?", f"SELECT COUNT(*) FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND p.paid_date IS NULL AND p.due_date<'2027-05-20'"),
 ("List the due dates of borrower 1007's missed payments, oldest first.", f"SELECT p.due_date FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND p.paid_date IS NULL AND p.due_date<'2027-05-20' ORDER BY p.due_date"),
 ("How many of borrower 1007's payments were made after their due date?", f"SELECT COUNT(*) FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND p.paid_date>p.due_date"),
 ("How many of borrower 1007's payments were made on or before the due date?", f"SELECT COUNT(*) FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND p.paid_date<=p.due_date"),
 ("When is the next payment due on borrower 1007's auto loan?", f"SELECT MIN(p.due_date) FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND l.product='auto' AND p.paid_date IS NULL AND p.due_date>='2027-05-20'"),
 ("What is the average payment amount on borrower 1007's auto loan, counting only payments made?", f"SELECT ROUND(AVG(p.amount),2) FROM payments p JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND l.product='auto' AND p.paid_date IS NOT NULL"),
 ("What fees has borrower 1007 been charged that were not waived? Give date, kind and amount.", f"SELECT f.charged, f.kind, f.amount FROM fees f JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND f.waived=0"),
 ("What is the total of borrower 1007's fees that were not waived?", f"SELECT ROUND(SUM(f.amount),2) FROM fees f JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND f.waived=0"),
 ("How much in fees has Harbor waived for borrower 1007?", f"SELECT ROUND(SUM(f.amount),2) FROM fees f JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND f.waived=1"),
 ("How many late fees has borrower 1007 been charged, waived or not?", f"SELECT COUNT(*) FROM fees f JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND f.kind='late'"),
 ("Has borrower 1007 had a deferral? List the start dates.", f"SELECT d.start_date FROM deferrals d JOIN loans l USING(loan_id) WHERE l.borrower_id={B}"),
 ("Is any of borrower 1007's loans in a deferral today? Give the last four digits.", f"SELECT l.last4 FROM deferrals d JOIN loans l USING(loan_id) WHERE l.borrower_id={B} AND d.start_date<='2027-05-20' AND date(d.start_date, '+'||d.months||' months')>='2027-05-20'"),
 ("Which of borrower 1007's loans has the highest balance? Give the last four digits.", f"SELECT last4 FROM loans WHERE borrower_id={B} AND balance=(SELECT MAX(balance) FROM loans WHERE borrower_id={B})"),
 ("Who is the borrower on the loan ending 7316?", "SELECT b.name FROM borrowers b JOIN loans l USING(borrower_id) WHERE l.last4='7316'"),
 ("How many borrowers have more than one loan?", "SELECT COUNT(*) FROM (SELECT borrower_id FROM loans GROUP BY borrower_id HAVING COUNT(*)>1)"),
 ("How many open loans have at least one missed payment?", "SELECT COUNT(DISTINCT l.loan_id) FROM loans l JOIN payments p USING(loan_id) WHERE l.status='open' AND p.paid_date IS NULL AND p.due_date<'2027-05-20'"),
 ("What is the total of late fees charged in April 2027 that were not waived?", "SELECT ROUND(SUM(amount),2) FROM fees WHERE kind='late' AND waived=0 AND charged BETWEEN '2027-04-01' AND '2027-04-30'"),
 ("How many borrowers have a missed payment but have never had a deferral?", "SELECT COUNT(DISTINCT l.borrower_id) FROM loans l JOIN payments p USING(loan_id) WHERE p.paid_date IS NULL AND p.due_date<'2027-05-20' AND l.borrower_id NOT IN (SELECT l2.borrower_id FROM deferrals d JOIN loans l2 USING(loan_id))"),
 ("Which borrower has the largest total open balance? Give the name.", "SELECT b.name FROM borrowers b JOIN loans l USING(borrower_id) WHERE l.status='open' GROUP BY b.borrower_id HAVING SUM(l.balance)=(SELECT MAX(s) FROM (SELECT SUM(balance) s FROM loans WHERE status='open' GROUP BY borrower_id))"),
 ("What is the average open balance of auto loans?", "SELECT ROUND(AVG(balance),2) FROM loans WHERE product='auto' AND status='open'"),
 ("How many payments across all loans were made late in April 2027?", "SELECT COUNT(*) FROM payments WHERE paid_date BETWEEN '2027-04-01' AND '2027-04-30' AND paid_date>due_date"),
]
FIRST = ["Emily", "Daniel", "Maria", "Jose", "Ashley", "Michael", "Jessica", "Luis", "Sarah", "David"]
LAST = ["Carter", "Nguyen", "Gonzalez", "Ramirez", "Thompson", "Hernandez", "Walker", "Lopez"]


def build(path, variety, seed=2026):
    rng = random.Random(seed)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path); con.executescript(SCHEMA)
    lid = pid = fid = did = 0
    for b in range(1001, 1041):
        con.execute("INSERT INTO borrowers VALUES (?,?)", (b, f"{rng.choice(FIRST)} {rng.choice(LAST)}"))
        prods = ["auto"] + (["personal"] if variety and (b <= 1020 or b == B) else [])
        for prod in prods:
            lid += 1
            last4 = "7316" if (b == B and prod == "auto") else f"{rng.randint(1000, 9999)}"
            status = "closed" if variety and prod == "personal" and b % 3 == 0 else "open"
            bal = 0.0 if status == "closed" else round(rng.uniform(2500, 21000), 2)
            con.execute("INSERT INTO loans VALUES (?,?,?,?,?,?,?)", (lid, b, prod, last4,
                        (date(2025, 1, 1) + timedelta(days=rng.randint(0, 600))).isoformat(), bal, status))
            amt = round(rng.uniform(240, 720), 2)
            dd = rng.randint(1, 25)
            for m in range(1, 7):                       # due Jan to Jun 2027
                due = date(2027, m, dd)
                if due >= date(2027, 5, 20):
                    paid = None
                elif variety and (rng.random() < 0.15 or (b == B and m == 3 and prod == "auto")):
                    paid = None
                else:
                    late = variety and rng.random() < 0.3
                    paid = due + timedelta(days=rng.randint(1, 12) if late else -rng.randint(0, 3))
                    if variety and b == B and prod == "personal" and m == 4:
                        paid = date(2027, 4, 9)        # same day as the auto payment below
                    if variety and b == B and prod == "auto" and m == 4:
                        paid = date(2027, 4, 9)
                pid += 1
                con.execute("INSERT INTO payments VALUES (?,?,?,?,?)", (pid, lid, due.isoformat(),
                            paid.isoformat() if paid else None, amt))
                if paid and paid > due or (paid is None and due < date(2027, 5, 20)):
                    fid += 1
                    waived = 1 if variety and (rng.random() < 0.4 or (b == B and m == 3)) else 0
                    con.execute("INSERT INTO fees VALUES (?,?,?,?,?,?)", (fid, lid, (due + timedelta(days=10)).isoformat(),
                                "late", 25.0 if prod == "auto" else 15.0, waived))
            if variety and rng.random() < 0.25 or (variety and b == B and prod == "auto"):
                did += 1
                start = date(2027, 4, 1) if b == B else date(2027, rng.randint(1, 5), 1)
                con.execute("INSERT INTO deferrals VALUES (?,?,?,?)", (did, lid, start.isoformat(), rng.choice([1, 2])))
    con.commit(); con.close()


PROMPT = """Write one SQLite query that answers the question from this read-only accounts database.

{schema}
{notes}

Question: {q}

Reply with the SQL only, no explanation, no Markdown."""


def gen(q):
    import anthropic
    msg = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=600, messages=[{"role": "user",
          "content": PROMPT.format(schema=SCHEMA, notes=NOTES, q=q)}])
    return msg.content[0].text


def clean_sql(t):
    t = re.sub(r"^\s*```(?:sql)?\s*|\s*```\s*$", "", t.strip())
    return t.strip().rstrip(";")


def norm_sql(s):
    return " ".join(re.sub(r"\s+", " ", s.lower()).replace(" ,", ",").split()).rstrip(";")


def run(db, sql):
    con = sqlite3.connect(db)
    try:
        rows = con.execute(sql).fetchall()
    except sqlite3.Error as e:
        return ("error", str(e))
    finally:
        con.close()
    return ("ok", rows)


def canon(rows):
    out = []
    for r in rows:
        out.append(tuple(round(v, 2) if isinstance(v, float) else v for v in r))
    return Counter(out)


def same(a, b, ordered=False):
    if a[0] != "ok" or b[0] != "ok":
        return False
    if ordered:
        return [tuple(round(v, 2) if isinstance(v, float) else v for v in r) for r in a[1]] == \
               [tuple(round(v, 2) if isinstance(v, float) else v for v in r) for r in b[1]]
    return canon(a[1]) == canon(b[1])


if __name__ == "__main__":
    dev, probe = OUT / "dev.db", OUT / "probe.db"
    build(dev, False); build(probe, True)
    cache = OUT / "sql-haiku.jsonl"
    if len(sys.argv) > 1 and sys.argv[1] == "run" and not cache.exists():
        with cf.ThreadPoolExecutor(6) as ex:
            res = list(ex.map(gen, [q for q, _ in Q]))
        cache.write_text("".join(json.dumps({"q": q, "raw": r}) + "\n" for (q, _), r in zip(Q, res)))
    gens = [json.loads(x) for x in cache.read_text().splitlines()]
    rows, n = [], len(Q)
    s_str = s_dev = s_probe = 0
    for i, ((q, gold), g) in enumerate(zip(Q, gens), 1):
        sql = clean_sql(g["raw"])
        ordered = "oldest first" in q
        a = same(run(dev, sql), run(dev, gold), ordered)
        b = same(run(probe, sql), run(probe, gold), ordered)
        st = norm_sql(sql) == norm_sql(gold)
        s_str += st; s_dev += a; s_probe += b
        rows.append({"n": i, "q": q, "sql": sql, "string": st, "dev": a, "probe": b,
                     "gold_probe": run(probe, gold)[1], "gen_probe": run(probe, sql)[1]})
    (OUT / "sql-scores.json").write_text(json.dumps(rows, indent=1, default=str))
    print(f"questions {n}; model {MODEL}")
    print(f"string match        {s_str:>2}/{n}")
    print(f"execution, dev.db   {s_dev:>2}/{n}")
    print(f"execution, probe.db {s_probe:>2}/{n}")
    print("pass on dev, fail on probe:", [r["n"] for r in rows if r["dev"] and not r["probe"]])
    print("fail on dev:", [r["n"] for r in rows if not r["dev"]])
