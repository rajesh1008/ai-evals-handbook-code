"""Chapter 15: the decision-step probe. REAL model calls.

A small fast model (claude-haiku-4-5-20251001, default sampling; this SDK takes no temperature argument) plays Compass's first-reply decision for
160 hardship cases whose facts are drawn in code first (Chapter 12's facts-first rule), so the required
action is known before any text exists. Eight segments of 20, one per policy branch the workshop gates
on, including the two Chapter 14 found missing from the gold generator: relief that ended exactly twelve
calendar months ago (the anniversary case) and a borrower who says their work has changed while the
account record shows the old status (the stated-work case).

Two prompts are compared on the same cases:
  hardship-prompt-p7   the production decision prompt (HP-2027-04 summary, HB-2027-07, the anniversary
                       sentence); it says nothing about stated work
  rc-0913-1            the same, plus the self-serve sentence proposed for the September release
  rc-0917-3            the production prompt, with the window computed in code and shown in the account
                       summary (a change to the eligibility tool, not to the wording)
  rc-0915-2            the production prompt plus two worked window examples (Victor's condition from
                       Chapter 13), dated away from the probe's own date so the example cannot leak an answer
The key is read from the environment by the SDK and never printed. Replies are cached in out/probe.jsonl.
Each prompt runs twice (rep 1 and rep 2) on the same cases, since sampling is not fixed.
Usage: python3 probe.py run   (calls the model for uncached rows), then python3 probe.py"""
import concurrent.futures as cf
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "ch12"))
from policy import POLICY_TEXT, ACTIONS  # noqa: E402

sys.path.insert(0, str(HERE.parents[0]))
import llm_backend as LB  # noqa: E402

LOCAL = LB.is_local()
MODEL = LB.model() if LOCAL else "claude-haiku-4-5-20251001"
RAW = LB.pick(HERE, HERE / "out" / "probe.jsonl", "probe-local.jsonl")
SEED = 2026
CONV_DAY = date(2027, 9, 14)

HB = ("Bulletin HB-2027-07 (Thu 15 July 2027): a disaster forbearance is not prior relief for 4.3.\n"
      "Window dates (September 2027 note): relief that ended on the same calendar date twelve months ago, or "
      "earlier, does not count; count from the date the relief ended, never the date it was granted.")
TASK = ("You are the decision step of Compass, Harbor Lending's servicing assistant. Read the account summary "
        "and the borrower's message, then choose the first-reply action the policy requires. Answer with JSON "
        "only, in the form {\"action\": \"<one of: ask_which_loan, ask_income, decline_window, "
        "refer_to_officer, draft_deferral>\"}.")
SELF_SERVE = ("Release note rc-0913-1: borrowers who have told you their monthly income should not have to wait "
              "for a call. When the borrower has stated a monthly income and has had no relief on this loan in the "
              "last twelve months, draft the deferral in this reply.")
WORKED = ("Worked examples for 4.3 (dates differ from any real case): today 3 March 2027, a payment extension "
          "ended 3 March 2026: that is twelve calendar months, so it does not count; continue to 4.5 and draft if "
          "nothing else applies. Today 3 March 2027, a deferral ended 4 March 2026: eleven months and some days, "
          "inside the window: decline_window. A payment extension counts as prior relief exactly as a deferral does.")
WINDOW_NOTE = ("The account summary's 4.3 window field is computed by the servicing core from the date the relief "
               "ended, in calendar months; use it for 4.3 rather than counting months yourself.")
PROMPTS = {"hardship-prompt-p7": "\n\n".join([TASK, POLICY_TEXT, HB]),
           "rc-0913-1": "\n\n".join([TASK, POLICY_TEXT, HB, SELF_SERVE]),
           "rc-0915-2": "\n\n".join([TASK, POLICY_TEXT, HB, WORKED]),
           "rc-0917-3": "\n\n".join([TASK, POLICY_TEXT, HB, WINDOW_NOTE])}
WINDOW_FIELD = {"rc-0917-3"}  # prompts whose account summary carries the window computed in code

SEGMENTS = ("employed_eligible", "self_employed_record", "self_employed_stated", "window_inside",
            "anniversary", "three_behind", "no_income", "two_loans_unnamed")
REQUIRED = {"employed_eligible": "draft_deferral", "self_employed_record": "refer_to_officer",
            "self_employed_stated": "refer_to_officer", "window_inside": "decline_window",
            "anniversary": "draft_deferral", "three_behind": "refer_to_officer", "no_income": "ask_income",
            "two_loans_unnamed": "ask_which_loan"}
CAUSE = ["my hours were cut at the warehouse", "I had surgery and missed three weeks of work",
         "my partner lost their job last month", "our rent went up and the car needed a new transmission",
         "the restaurant I work at closed for renovation", "I was off sick for most of August"]
STATED = ["I left my job in March and I've been driving for a delivery app since, so it's all freelance now",
          "I went out on my own in the spring, I do bookkeeping for small businesses as a contractor now",
          "I'm self-employed now, I started cleaning houses for my own clients after the layoff",
          "since June I've been working for myself doing repairs, no more paycheck from the shop"]


def months_back(d, m):
    y, mo = d.year, d.month - m
    while mo <= 0:
        mo += 12; y -= 1
    return date(y, mo, min(d.day, 28 if mo == 2 else 30 if mo in (4, 6, 9, 11) else 31))


def cases(seed=SEED):
    g = random.Random(seed)
    out = []
    for seg in SEGMENTS:
        for i in range(20):
            income = g.randrange(1900, 5600, 50)
            c = {"id": f"pr-{len(out) + 1:03d}", "segment": seg, "required": REQUIRED[seg], "loans": 1,
                 "work_record": "employed (payroll)", "behind": g.choice([0, 1, 1, 2]), "relief": None,
                 "income_text": f"I bring home about ${income:,} a month" if g.random() < 0.5 else f"my gross pay is ${income:,} a month",
                 "cause": g.choice(CAUSE), "stated_work": ""}
            if seg == "self_employed_record":
                c["work_record"] = "self-employed (1099 income on file)"
            if seg == "self_employed_stated":
                c["stated_work"] = g.choice(STATED)
            if seg == "window_inside":
                m = g.choice([3, 5, 7, 9, 10, 11])
                c["relief"] = ("deferral" if g.random() < 0.6 else "payment extension", months_back(CONV_DAY, m))
            if seg == "anniversary":
                c["relief"] = ("deferral" if g.random() < 0.6 else "payment extension", months_back(CONV_DAY, 12))
            if seg == "three_behind":
                c["behind"] = g.choice([3, 3, 4])
            if seg == "no_income":
                c["income_text"] = ""
            if seg == "two_loans_unnamed":
                c["loans"] = 2
            out.append(c)
    return out


def window_field(c):
    """The 4.3 answer computed in code: whole calendar months from the end date to today (12 on the anniversary)."""
    if not c["relief"]:
        return "no prior relief"
    end = c["relief"][1]
    m = (CONV_DAY.year - end.year) * 12 + CONV_DAY.month - end.month - (CONV_DAY.day < end.day)
    return f"{m} calendar months since relief ended; inside the 12-month window: {'yes' if m < 12 else 'no'}"


def render(c, window=False):
    loans = ("two loans: auto loan ending 4417 and personal loan ending 5586" if c["loans"] == 2
             else "one loan: auto loan ending 4417")
    rel = "none on record"
    if c["relief"]:
        kind, end = c["relief"]
        rel = f"{kind} on this loan, ended {end.day} {end:%B %Y}"
    msg = f"Hi, {c['cause']} and I can't make my next payment."
    if c["stated_work"]:
        msg += f" {c['stated_work'][0].upper()}{c['stated_work'][1:]}."
    if c["income_text"]:
        msg += f" Right now {c['income_text']}."
    msg += " Is there anything you can do?" if c["loans"] == 1 else " Can you help me with my loan?"
    return (f"Today's date: {CONV_DAY.day} {CONV_DAY:%B %Y}\nAccount summary (servicing core): {loans}; "
            f"payments behind: {c['behind']}; employment on file: {c['work_record']}; prior relief: {rel}"
            + (f"; 4.3 window: {window_field(c)}" if window else "") + "\n"
            f"Borrower's message: {msg}")


def call(job):
    pv, c, rep = job
    if LOCAL:
        r = LB.chat(render(c, pv in WINDOW_FIELD), system=PROMPTS[pv], max_tokens=60, temperature=0.7)
        return {"id": c["id"], "prompt": pv, "rep": rep, "raw": r["text"], "in_tok": r["in_tok"],
                "out_tok": r["out_tok"], "model": r["model"], "label": LB.LABEL}
    import anthropic
    msg = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=60, system=PROMPTS[pv],
                                                messages=[{"role": "user", "content": render(c, pv in WINDOW_FIELD)}])
    return {"id": c["id"], "prompt": pv, "rep": rep, "raw": msg.content[0].text, "in_tok": msg.usage.input_tokens,
            "out_tok": msg.usage.output_tokens}


def cached():
    return {(j["id"], j["prompt"], j.get("rep", 1)): j for j in map(json.loads, RAW.read_text().splitlines())} if RAW.exists() else {}


def complete(C=None):
    """True when every case, prompt and rep has a cached reply (the book's run, or a finished local run)."""
    C = cached() if C is None else C
    return bool(C) and all((c["id"], pv, rep) in C for c in cases() for pv in PROMPTS for rep in (1, 2))


def action(raw):
    """The action named in the JSON object. Most replies add a reasoning note after the JSON that names every
    action it ruled out, so the first action word in the text is not the answer (the first parser did that)."""
    m = re.search(r'"action"\s*:\s*"([a-z_]+)"', raw)
    return m.group(1) if m and m.group(1) in ACTIONS else "unparsed"


def naive_action(raw):
    """The first parser: the first action word anywhere in the reply. Kept for the Lab's parser comparison."""
    for a in ACTIONS:
        if a in raw:
            return a
    return "unparsed"


def results(rep=1):
    C, rows = cached(), []
    for c in cases():
        for pv in PROMPTS:
            r = C.get((c["id"], pv, rep))
            if r:
                rows.append({**c, "prompt": pv, "action": action(r["raw"]), "relief": None})
    return rows, C


def report():
    C = cached()
    print(f"== Decision-step probe ({LB.LABEL if LOCAL else 'REAL'}, {MODEL}, default sampling; this SDK takes no temperature argument): "
          f"{len(C)} calls cached, {sum(c['in_tok'] for c in C.values()):,} input / "
          f"{sum(c['out_tok'] for c in C.values()):,} output tokens")
    cs = {c["id"]: c for c in cases()}
    naive = sum(naive_action(r["raw"]) == cs[i]["required"] for (i, pv, rep), r in C.items() if rep == 1 and pv == "hardship-prompt-p7")
    fixed = sum(action(r["raw"]) == cs[i]["required"] for (i, pv, rep), r in C.items() if rep == 1 and pv == "hardship-prompt-p7")
    print(f"  parser check, production prompt, rep 1: first-action-word parser {naive}/160 right; JSON parser {fixed}/160 right; "
          f"{sum(len(r['raw']) > 45 for r in C.values())} of {len(C)} replies add reasoning after the JSON")
    out = {"model": MODEL, "calls": len(C), "in_tok": sum(c['in_tok'] for c in C.values()),
           "out_tok": sum(c['out_tok'] for c in C.values()), "naive": naive, "fixed": fixed, "seg": {}}
    for pv in PROMPTS:
        print(f"  {pv} (rep 1 / rep 2)")
        for seg in SEGMENTS:
            per = []
            for rep in (1, 2):
                rs = [(cs[i], action(r["raw"])) for (i, p, rp), r in C.items() if p == pv and rp == rep and cs[i]["segment"] == seg]
                per.append((sum(a == c["required"] for c, a in rs), len(rs), dict(Counter(a for c, a in rs if a != c["required"]))))
            out["seg"][f"{pv}|{seg}"] = per
            print(f"    {seg:22s} {REQUIRED[seg]:17s} right {per[0][0]:2d}/{per[0][1]} {per[1][0]:2d}/{per[1][1]}  "
                  f"wrong {per[0][2]} | {per[1][2]}")
        for rep in (1, 2):
            rs = [(cs[i], action(r["raw"])) for (i, p, rp), r in C.items() if p == pv and rp == rep]
            right = sum(a == c["required"] for c, a in rs)
            offers = sum(a == "draft_deferral" and c["required"] != "draft_deferral" for c, a in rs)
            refus = sum(a != "draft_deferral" and c["required"] == "draft_deferral" for c, a in rs)
            ext = sum(a == "draft_deferral" and c["segment"] == "window_inside" and c["relief"][0] == "payment extension" for c, a in rs)
            out[f"{pv}|{rep}"] = {"right": right, "n": len(rs), "wrong_offers": offers, "wrongful_refusals": refus, "ext_offers": ext}
            print(f"    rep {rep}: right {right}/{len(rs)}; wrong offers {offers} ({ext} after a payment extension); "
                  f"eligible borrowers not offered {refus}")
    agree = sum(action(C[(i, pv, 1)]["raw"]) == action(C[(i, pv, 2)]["raw"]) for i in cs for pv in PROMPTS)
    out["rep_agree"] = agree
    print(f"  rep 1 and rep 2 chose the same action on {agree} of {len(PROMPTS) * len(cs)} case-prompt pairs")
    return out


if __name__ == "__main__":
    if LOCAL:
        LB.require_local(); LB.banner("decision-step probe")
    if LB.live_requested(sys.argv) or LOCAL:
        done = cached()
        jobs = [(pv, c, rep) for rep in (1, 2) for c in cases() for pv in PROMPTS if (c["id"], pv, rep) not in done]
        RAW.parent.mkdir(exist_ok=True)
        with cf.ThreadPoolExecutor(6) as ex, RAW.open("a") as fh:
            for r in ex.map(call, jobs):
                fh.write(json.dumps(r) + "\n"); fh.flush()
    if not complete():
        LB.skip("probe.py (REAL decision-step probe)", "out/probe.jsonl", "./run_all.sh run")
        sys.exit(0)
    summary = report()
    LB.pick(HERE, HERE / "out" / "probe.json").write_text(json.dumps(summary, indent=1))
