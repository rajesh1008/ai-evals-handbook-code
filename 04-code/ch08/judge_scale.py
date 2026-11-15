"""Chapter 8, real model run: does a model reader rate longer fee replies higher on a 1-to-5 scale,
and does the binary MC-02 question resist that? Run 1 November 2026 with ANTHROPIC_API_KEY.

Replies are written from templates (the fixture has facts, not text); every fee value is
illustrative. Each of 40 fee cases gets a short and a long reply with the same correctness; the
long one recites extra schedule terms that are all in the tool span. Truth comes from the template.
Model: claude-haiku-4-5-20251001, default temperature, each prompt asked twice. Seed 2026.
Usage: python3 judge_scale.py run   (calls the API, caches out/judge_raw.jsonl)
       python3 judge_scale.py       (analyses the cache only)
"""
import json, random, re, sys, concurrent.futures as cf
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.metrics import weighted_kappa  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = HERE / "out" / "judge_raw.jsonl"
MODEL = "claude-haiku-4-5-20251001"
SCHEDULE = ["Returned payment fee is $15.", "Grace period is 15 days after the due date.",
            "Late fee is $25, charged once per missed payment.", "Phone payments carry no fee.",
            "Payoff letters are free once a year.", "Lien releases are sent within ten business days of payoff.",
            "Autopay borrowers receive one courtesy waiver every twelve months.",
            "Fees are shown on the monthly statement under Charges."]
KINDS = ["right_no"] * 8 + ["right_waive"] * 7 + ["deferred"] * 10 + ["F_waive"] * 6 + ["X_wrongloan"] * 5 + ["X_invent"] * 4


def case(i, kind):
    g = random.Random(f"judge-{i}")
    asked, other = f"{g.randint(1000, 9999)}", f"{g.randint(1000, 9999)}"
    day = g.randint(16, 28)
    q = f"Why was I charged a late fee on my loan ending {asked}? I paid {day} days after the due date."
    status = {"right_no": "fee_stands", "right_waive": "waive", "deferred": "review", "F_waive": "waive",
              "X_wrongloan": "fee_stands", "X_invent": None}[kind]
    loan = other if kind == "X_wrongloan" else asked
    tool = ('fee_lookup(loan="%s") -> ERROR timeout' % asked if kind == "X_invent" else
            'fee_lookup(loan="%s") -> {"late_fee": 25, "grace_days": 15, "waiver": "%s", "schedule": %s}'
            % (loan, status, json.dumps(SCHEDULE)))
    if kind in ("right_no", "X_wrongloan", "X_invent"):
        core = f"The $25 late fee on your loan ending {asked} stands, because the payment arrived after the 15-day grace period."
    elif kind in ("right_waive",):
        core = f"The $25 late fee on your loan ending {asked} has been waived, so you do not owe it."
    elif kind == "F_waive":
        core = f"The $25 late fee on your loan ending {asked} stands and cannot be waived."
    else:
        core = f"A waiver request is open on your loan ending {asked}, so a loan officer will confirm within two business days whether the $25 fee is removed."
    extra = " ".join(g.sample([s for s in SCHEDULE if "Late fee" not in s and "Grace" not in s], 4))
    truth = "fail" if kind in ("F_waive", "X_wrongloan", "X_invent") else ("deferred" if kind == "deferred" else "pass")
    return {"case": i, "kind": kind, "truth": truth, "question": q, "tool": tool,
            "short": core, "long": core + " For reference, here is how our fees work. " + extra + " Let me know if anything else is unclear."}


BIN = """You check a loan servicing assistant's reply. Borrower asked: {q}
Tool span: {tool}
Reply: {reply}
Question: did the reply state a fee amount, grace period or waiver status that differs from what the fee tool returned, or would have returned, for the loan the borrower named? A reply that hands the waiver to a loan officer because the tool says review is DEFERRED. Answer with one word on the last line: PASS, FAIL or DEFERRED."""
LIK = """You check a loan servicing assistant's reply. Borrower asked: {q}
Tool span: {tool}
Reply: {reply}
Rate how well the reply explains the fee, from 1 (very poor) to 5 (excellent). Answer with the number alone on the last line."""


def items():
    cases = [case(i, k) for i, k in enumerate(KINDS)]
    for c in cases:
        for ln in ("short", "long"):
            for scale, tpl in (("binary", BIN), ("likert", LIK)):
                for rep in (1, 2):
                    yield c, ln, scale, rep, tpl.format(q=c["question"], tool=c["tool"], reply=c[ln])


def call(args):
    import anthropic
    c, ln, scale, rep, prompt = args
    msg = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=300, messages=[{"role": "user", "content": prompt}])
    text = msg.content[0].text.strip()
    return {"case": c["case"], "kind": c["kind"], "truth": c["truth"], "len": ln, "words": len(c[ln].split()),
            "scale": scale, "rep": rep, "answer": text.splitlines()[-1].strip(), "model": msg.model,
            "in_tok": msg.usage.input_tokens, "out_tok": msg.usage.output_tokens}


def run():
    with cf.ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(call, list(items())))
    RAW.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def parse(r):
    a = r["answer"].upper()
    if r["scale"] == "binary":
        m = re.search(r"PASS|FAIL|DEFERRED", a)
        return m.group(0).lower() if m else None
    m = re.search(r"[1-5]", a)
    return int(m.group(0)) if m else None


def kappa2(a, b):
    lv = sorted(set(a) | set(b)); n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in lv)
    return (po - pe) / (1 - pe)


def analyse():
    rows = [json.loads(l) for l in RAW.read_text().splitlines()]
    for r in rows: r["v"] = parse(r)
    g = {(r["case"], r["len"], r["scale"], r["rep"]): r for r in rows}
    n_cases = len(KINDS)
    print(f"model {rows[0]['model']}; calls {len(rows)}; unparsed {sum(r['v'] is None for r in rows)}; "
          f"tokens in {sum(r['in_tok'] for r in rows)}, out {sum(r['out_tok'] for r in rows)}")
    b = [r for r in rows if r["scale"] == "binary" and r["v"]]
    acc = sum(r["v"] == r["truth"] for r in b) / len(b)
    print(f"binary: agreement with planted truth {acc:.1%} of {len(b)}; kappa {kappa2([r['v'] for r in b], [r['truth'] for r in b]):.2f}")
    for ln in ("short", "long"):
        x = [r for r in b if r["len"] == ln]
        fails = sum(r["v"] == "fail" for r in x)
        print(f"  {ln}: agreement {sum(r['v'] == r['truth'] for r in x) / len(x):.1%}; FAIL verdicts {fails} of {len(x)} (truth {sum(r['truth'] == 'fail' for r in x)})")
    fp = [g[(c, ln, 'binary', 1)]["v"] != g[(c, ln, 'binary', 2)]["v"] for c in range(n_cases) for ln in ("short", "long")
          if g[(c, ln, 'binary', 1)]["v"] and g[(c, ln, 'binary', 2)]["v"]]
    flips = sum(fp)
    lp = [g[(c, 'short', 'binary', 1)]["v"] != g[(c, 'long', 'binary', 1)]["v"] for c in range(n_cases)
          if g[(c, 'short', 'binary', 1)]["v"] and g[(c, 'long', 'binary', 1)]["v"]]
    lflip = sum(lp)
    print("  unparsed:", [(r["scale"], r["kind"], r["len"], r["answer"][:50]) for r in rows if r["v"] is None])
    print(f"  same reply asked twice, verdict changed: {flips} of {len(fp)}; short vs long of same case changed (run 1): {lflip} of {len(lp)}")
    wrong = [(r["truth"], r["v"]) for r in b if r["v"] != r["truth"]]
    print("  disagreements (truth, model):", sorted(set((t, v, wrong.count((t, v))) for t, v in wrong)))
    L = [r for r in rows if r["scale"] == "likert" and r["v"]]
    for t in ("pass", "deferred", "fail"):
        s = [r["v"] for r in L if r["truth"] == t and r["len"] == "short"]; l = [r["v"] for r in L if r["truth"] == t and r["len"] == "long"]
        print(f"1-to-5 {t}: mean short {sum(s) / len(s):.2f}, long {sum(l) / len(l):.2f}")
    right = [c for c in range(n_cases) if g[(c, 'short', 'likert', 1)]["truth"] == "pass"]
    right = [c for c in right if g[(c, 'long', 'likert', 1)]["v"] and g[(c, 'short', 'likert', 1)]["v"]]
    hi = sum(g[(c, 'long', 'likert', 1)]["v"] > g[(c, 'short', 'likert', 1)]["v"] for c in right)
    lo = sum(g[(c, 'long', 'likert', 1)]["v"] < g[(c, 'short', 'likert', 1)]["v"] for c in right)
    print(f"  right replies, run 1: long scored higher {hi}, lower {lo}, same {len(right) - hi - lo} of {len(right)}")
    a1 = [g[(c, ln, 'likert', 1)]["v"] for c in range(n_cases) for ln in ("short", "long")]
    a2 = [g[(c, ln, 'likert', 2)]["v"] for c in range(n_cases) for ln in ("short", "long")]
    pr = [(x, y) for x, y in zip(a1, a2) if x and y]; a1, a2 = [x for x, _ in pr], [y for _, y in pr]
    print(f"  same reply asked twice ({len(pr)} pairs both parsed): exact {sum(x == y for x, y in zip(a1, a2)) / len(a1):.1%}, weighted kappa {weighted_kappa(a1, a2):.2f}")
    for cut in (1, 2, 3):
        k = sum(r["v"] <= cut for r in L if r["rep"] == 1)
        kf = sum(r["v"] <= cut for r in L if r["rep"] == 1 and r["truth"] == "fail")
        print(f"  run 1, scored {cut} or less: {k} of {sum(r['rep'] == 1 for r in L)}, of which wrong {kf} (truth fail {sum(r['truth'] == 'fail' for r in L if r['rep'] == 1)})")
    fs = [r["v"] for r in L if r["truth"] == "fail"]
    print(f"  wrong replies' scores (both runs): " + ", ".join(f"{v}:{fs.count(v)}" for v in range(1, 6)))


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        run()
    analyse()
