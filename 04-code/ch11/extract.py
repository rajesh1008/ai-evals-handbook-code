"""Chapter 11: Compass's income-verification extraction, run for real on the 200 documents.

Prompt extract-prompt-v1 (the field definitions are guideline v3's, written with Grace Holloway and
Ben Fletcher). One call per document at the default temperature; the model returns the twelve fields, the payroll-deposit
table and a confidence from 0 to 1 per field. Raw text is cached, so the lab runs without a key.
Models: claude-haiku-4-5-20251001 (Compass's extractor) and claude-sonnet-4-6 (second reader).
Usage: python3 extract.py run haiku|sonnet     (needs ANTHROPIC_API_KEY; never printed)
       python3 extract.py                       (prints what is cached)
"""
import json, re, sys, concurrent.futures as cf
from pathlib import Path
import docs as DOCS

HERE = Path(__file__).resolve().parent
MODELS = {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-4-6"}
PROMPT_VERSION = "extract-prompt-v1"
FIELDS = ["doc_type", "person_name", "employer", "period_end", "pay_frequency", "gross_pay", "net_pay", "ytd_gross",
          "payroll_total", "stated_monthly_income", "loan_last4", "hardship_reason"]
PROMPT = """You extract income-verification fields from a document a borrower uploaded to Harbor Lending for a hardship request. The text below came from the document service after OCR and may contain character errors.

Fields (use null when the document does not state the value; never compute a value the document does not state):
- doc_type: "pay_stub", "bank_statement" or "hardship_letter"
- person_name: the borrower's name as printed (employee, account holder or letter signer)
- employer: the employer's name (pay stub: the company; bank statement: the payroll payer named in the deposit description; letter: only if the letter names it)
- period_end: ISO date YYYY-MM-DD. Pay stub: the last day of the pay period (not the pay date). Bank statement: the last day of the statement period. Letter: the date the letter is dated.
- pay_frequency: "weekly", "biweekly", "semimonthly" or "monthly"; pay stubs only. If not printed, infer it from the pay period dates (7 days weekly, 14 days biweekly, 1st-15th or 16th-end semimonthly, whole month monthly).
- gross_pay: pay stub, the current period's gross pay as a number (if only earnings lines are printed, their sum)
- net_pay: pay stub, the current period's net pay
- ytd_gross: pay stub, year-to-date gross pay
- payroll_total: bank statement, the sum of payroll (direct deposit from an employer) deposits posted inside the statement period; exclude transfers, refunds, tax refunds, person-to-person payments, cash or mobile deposits and anything pending
- stated_monthly_income: letter, a monthly income amount the borrower states, as stated (gross or net); null if the letter gives only an hourly rate or no figure
- loan_last4: letter, the last four digits of the loan the request is about (not any other loan mentioned)
- hardship_reason: letter, one of "job_loss", "reduced_hours", "medical", "divorce_separation", "death_in_family", "disaster": the event the borrower says caused the payment problem; if several are mentioned, the first one described as the cause
- payroll_deposits: bank statement, list of {{"date": "YYYY-MM-DD", "amount": number}} for each payroll deposit counted in payroll_total; null for other documents

Also give confidence: an object with a number from 0 to 1 for each of the twelve fields above, your probability that the value you gave (including null) is correct.

Return one JSON object with exactly these keys: the twelve fields, "payroll_deposits" and "confidence". No other text.

Document:
<<<
{text}
>>>"""


def raw_path(m):
    return HERE / "out" / f"extract-{m}.jsonl"


def call(args):
    import anthropic
    m, d = args
    client = anthropic.Anthropic()
    msg = client.messages.create(model=MODELS[m], max_tokens=1500,
                                 messages=[{"role": "user", "content": PROMPT.format(text=d["text"])}])
    return {"id": d["id"], "model": MODELS[m], "prompt": PROMPT_VERSION, "raw": msg.content[0].text,
            "in_tok": msg.usage.input_tokens, "out_tok": msg.usage.output_tokens}


def load(m):
    p = raw_path(m)
    return {j["id"]: j for j in map(json.loads, p.read_text().splitlines())} if p.exists() else {}


def parse(raw):
    """Layer one starts here: does the reply parse as one JSON object?"""
    t = raw.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "run":
        m = sys.argv[2]
        done = load(m)
        todo = [(m, d) for d in DOCS.load() if d["id"] not in done]
        with cf.ThreadPoolExecutor(6) as ex, raw_path(m).open("a") as fh:
            for res in ex.map(call, todo):
                fh.write(json.dumps(res, ensure_ascii=False) + "\n"); fh.flush()
    for m in MODELS:
        c = load(m)
        if c:
            print(f"{MODELS[m]}: {len(c)} documents cached, prompt {PROMPT_VERSION}, "
                  f"{sum(x['in_tok'] for x in c.values()):,} input / {sum(x['out_tok'] for x in c.values()):,} output tokens")
