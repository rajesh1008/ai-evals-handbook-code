"""Chapter 9: where a code check beats a model judge, and where it does not. A real run on a small sample.
Model: claude-haiku-4-5-20251001, each prompt twice (temperature default). Three tasks:
  A. approval sentence  - 40 April offer replies (all seven wordings); judge vs C-04 v2.0 vs Victor's ruling
  B. payoff arithmetic  - 40 April payoff conversations (20 that C-07 passes, 20 it fails); judge vs C-07
  C. waiver language    - 30 fee replies the model writes itself (15 confirm a waiver, 15 refuse one);
                          judge vs C-06's regex, with and without the negation rule
Usage: python3 judge_vs_code.py run   (calls the API; ANTHROPIC_API_KEY from the environment, never printed)
       python3 judge_vs_code.py       (analyses the cache in out/judge_vs_code.jsonl)"""
import json
import random
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
sys.path.insert(0, str(HERE.parents[0] / "ch07"))
sys.path.insert(0, str(HERE.parents[0] / "ch08"))
from truss import checks as K  # noqa: E402
import april as A  # noqa: E402
import compass_checks as CC  # noqa: E402

MODEL = "claude-haiku-4-5-20251001"
CACHE = HERE / "out" / "judge_vs_code.jsonl"
GEN = HERE / "out" / "waiver_paraphrases.json"
CACHE.parent.mkdir(exist_ok=True)

P_APPROVAL = """You check replies from a loan servicer's assistant against one disclosure rule.
Rule (Hardship policy HP-2027-04, section 4.4): any deferral offer must tell the borrower, in English or Spanish,
that a loan officer must approve the offer before it takes effect. The borrower must not be told the offer is
already approved or that the deferral will start without approval being needed.

Reply:
<<<{reply}>>>

Does the reply meet the rule? Answer on the first line with exactly PASS or FAIL, then one sentence of reason."""

P_PAYOFF = """You check payoff quotes from a loan servicer's assistant.
Policy PL-2026-01 section 2: a payoff quote is good through ten calendar days after the quote date; if that day is a
Sunday it moves to the Monday, and interest is counted to the good-through date.
Interest accrues daily on the principal at the loan's APR using the loan's day-count convention
(actual/365: principal x APR / 365 per day; actual/360: principal x APR / 360 per day), from the interest-from date.
Payoff = principal + interest from interest_from up to and including no day after good_through + fees due.
Round money to the cent.

Loan record: {loan}
Payoff tool result: {quote}
Reply to the borrower:
<<<{reply}>>>

Are the payoff amount, the per diem and the good-through date in the tool result and in the reply all correct?
Answer on the first line with exactly PASS or FAIL, then one sentence naming the wrong figure if any."""

P_WAIVED = """A borrower asked about a $25.00 late fee. Here is the servicer's reply:
<<<{reply}>>>

Does the reply tell the borrower that the fee HAS BEEN waived (removed, reversed, credited back)?
Answer on the first line with exactly YES or NO, then one sentence of reason."""

P_GEN = """Write {n} different short replies (one or two sentences each) that a loan servicer's assistant might send
about a $25.00 late fee on a loan ending 4821. {what}
Vary the wording widely: plain, formal, apologetic, with and without the words "waive", "remove", "reverse",
"credit", "refund", and include some sentences that contain a negation near those words. Do not mention any other
amount. Return only a JSON list of strings."""


def items():
    rows = A.build()
    apr = [A.render(r) for r in rows]
    S = CC.suite()
    res, _ = S.run_all(apr)
    g = random.Random(2026)
    out = []
    offers = [t for t in apr if CC.spans(t, "draft_offer")]
    quota = {"canonical": 10, "para-A": 6, "para-B": 6, "para-C": 6, "missing": 6, "es-canonical": 3, "es-para": 3}
    for tag, n in quota.items():
        pool = sorted([t for t in offers if t["meta"]["approval"] == tag], key=lambda t: t["trace_id"])
        for t in g.sample(pool, min(n, len(pool))):
            out.append({"task": "approval", "id": t["trace_id"], "tag": tag, "reply": t["reply"],
                        "code": res[t["trace_id"]]["C-04"].outcome,
                        "truth": "fail" if tag in ("para-C", "missing") else "pass"})
    pay = [t for t in apr if t["flow"] == "payoff_letter" and res[t["trace_id"]]["C-07"].outcome in (K.PASS, K.FAIL)]
    ok = sorted([t for t in pay if res[t["trace_id"]]["C-07"].outcome == K.PASS], key=lambda t: t["trace_id"])
    bad_tool = sorted([t for t in pay if res[t["trace_id"]]["C-07"].data.get("side") == "tool"], key=lambda t: t["trace_id"])
    bad_reply = sorted([t for t in pay if res[t["trace_id"]]["C-07"].data.get("side") == "reply"], key=lambda t: t["trace_id"])
    for kind, pool, n in (("correct", ok, 20), ("tool short (Sunday)", bad_tool, 10), ("reply differs", bad_reply, 10)):
        for t in g.sample(pool, n):
            q = CC.spans(t, "get_payoff_quote")[0]
            loan = CC.loan_rec(t, q["args"]["loan_id"])
            lr = {k: loan[k] for k in ("loan_id", "principal", "apr", "day_count")}
            out.append({"task": "payoff", "id": t["trace_id"], "tag": kind, "reply": t["reply"],
                        "loan": json.dumps(lr, default=float), "quote": json.dumps(q["result"]),
                        "code": res[t["trace_id"]]["C-07"].outcome, "truth": "pass" if kind == "correct" else "fail"})
    return out


def ask(prompt, max_tokens=300):
    import anthropic
    t0 = time.perf_counter()
    msg = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
    txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return txt, msg.usage.input_tokens, msg.usage.output_tokens, time.perf_counter() - t0


def paraphrases(live):
    if GEN.exists():
        return json.loads(GEN.read_text())
    if not live:
        sys.exit("no paraphrases cached; run with 'run'")
    out = {}
    for key, what in (("confirm", "In every reply the fee HAS BEEN waived (removed from the account)."),
                      ("refuse", "In every reply the fee STANDS and will NOT be waived.")):
        txt, i, o, s = ask(P_GEN.format(n=15, what=what), max_tokens=2000)
        lst = json.loads(re.search(r"\[.*\]", txt, re.S).group(0))
        out[key] = lst[:15]
        out[f"{key}_usage"] = [i, o, s]
    GEN.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def main(live):
    its = items()
    par = paraphrases(live)
    for key in ("confirm", "refuse"):
        for i, p in enumerate(par[key]):
            its.append({"task": "waiver", "id": f"{key}-{i:02d}", "tag": key, "reply": p,
                        "truth": "waived" if key == "confirm" else "not waived"})
    done = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            x = json.loads(line)
            done[(x["task"], x["id"], x["rep"])] = x
    todo = []
    for it in its:
        for rep in (0, 1):
            if (it["task"], it["id"], rep) not in done:
                todo.append((it, rep))
    if todo and live:
        def run(arg):
            it, rep = arg
            prompt = {"approval": P_APPROVAL, "payoff": P_PAYOFF, "waiver": P_WAIVED}[it["task"]].format(**it)
            txt, i, o, s = ask(prompt)
            return {"task": it["task"], "id": it["id"], "rep": rep, "text": txt, "in_tok": i, "out_tok": o, "sec": s}
        with ThreadPoolExecutor(8) as ex, CACHE.open("a") as fh:
            for x in ex.map(run, todo):
                fh.write(json.dumps(x, ensure_ascii=False) + "\n")
                done[(x["task"], x["id"], x["rep"])] = x
    elif todo:
        print(f"{len(todo)} calls not cached; run with 'run'")
        return
    analyse(its, done, par)


def code_reads(it, negation):
    """Run C-06 itself on a fee trace whose tool says 'waive' (confirm) or 'no' (refuse); a pass means the check
    read the reply the way its author meant. Returns what the check took the reply to say."""
    ws = "waive" if it["tag"] == "confirm" else "no"
    t = {"reply": it["reply"], "spans": [{"tool": "get_fee_schedule", "args": {"loan_id": "4100004821"}, "status": "ok",
         "result": {"loan_id": "4100004821", "fee_type": "late", "amount": 25.0, "assessed_on": "2027-04-02",
                    "days_late": 22, "grace_days": 15, "waive_status": ws, "schedule": "FS-2026-02"}}]}
    r = CC.fee_figures_v("1.1", negation)(t, {})
    ok = r.outcome == K.PASS
    return it["truth"] if ok else ("not waived" if it["truth"] == "waived" else "waived")


def first_word(txt):
    w = re.match(r"\W*(\w+)", txt or "")
    return w.group(1).upper() if w else "?"


def analyse(its, done, par):
    R = {}
    calls = list(done.values())
    print(f"model {MODEL}; calls {len(calls) + 2} (2 to write the paraphrases); input tokens "
          f"{sum(c['in_tok'] for c in calls) + par['confirm_usage'][0] + par['refuse_usage'][0]:,}; output tokens "
          f"{sum(c['out_tok'] for c in calls) + par['confirm_usage'][1] + par['refuse_usage'][1]:,}; "
          f"median latency {sorted(c['sec'] for c in calls)[len(calls) // 2]:.2f} s")
    for task in ("approval", "payoff", "waiver"):
        sub = [it for it in its if it["task"] == task]
        print(f"\n== {task}: {len(sub)} items, each judged twice")
        flips, jt, rows = 0, Counter(), []
        for it in sub:
            a, b = (first_word(done[(task, it["id"], r)]["text"]) for r in (0, 1))
            flips += a != b
            if task == "waiver":
                j = "waived" if a == "YES" else "not waived"
                rx, rxn = (code_reads(it, neg) for neg in (False, True))
                rows.append((it["tag"], it["truth"], j, rx, rxn, it["reply"]))
            else:
                j = "pass" if a == "PASS" else "fail"
                rows.append((it["tag"], it["truth"], j, it["code"], it["id"]))
        if task == "waiver":
            for name, k in (("judge", 2), ("regex v1.1", 3), ("regex + negation", 4)):
                ok = sum(r[1] == r[k] for r in rows)
                print(f"  {name:<18} agrees with intent {ok}/{len(rows)}")
                R[f"waiver_{name}"] = [ok, len(rows)]
            for r in rows:
                if r[1] != r[4] or r[1] != r[2]:
                    print(f"    intent {r[1]:<10} judge {r[2]:<10} regex+neg {r[4]:<10} | {r[5][:110]}")
        else:
            by = Counter()
            for r in rows:
                by[(r[0], r[2], r[3])] += 1
            jok = sum(r[1] == r[2] for r in rows)
            cok = sum(r[1] == r[3] for r in rows)
            print(f"  judge agrees with truth {jok}/{len(rows)}; code check agrees {cok}/{len(rows)}")
            for (tag, j, c), n in sorted(by.items()):
                print(f"    {tag:<22} judge {j:<5} code {c:<5} {n}")
            R[f"{task}_judge"] = [jok, len(rows)]
            R[f"{task}_code"] = [cok, len(rows)]
            R[f"{task}_cells"] = {f"{a}|{b}|{c}": n for (a, b, c), n in by.items()}
        print(f"  judge flips between the two runs: {flips} of {len(sub)}")
        R[f"{task}_flips"] = [flips, len(sub)]
    R["calls"] = len(calls) + 2
    R["tokens"] = [sum(c["in_tok"] for c in calls), sum(c["out_tok"] for c in calls)]
    (HERE / "out" / "judge_vs_code.json").write_text(json.dumps(R, indent=1))


if __name__ == "__main__":
    main(len(sys.argv) > 1 and sys.argv[1] == "run")
