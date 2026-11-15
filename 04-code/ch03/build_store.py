"""Chapter 3 fixture: rebuild the pilot as a v0.5 trace store.

Harbor Lending and Compass are fictional. From seed 2026 this module derives,
for each of the 24,011 pilot traces in compass_pilot.db: the trace-level
settings (model, prompt and policy versions), a span tree (agent, router, one
chat span per turn, tool and retrieval spans), redacted messages, and the
outcomes the servicing system and contact centre recorded afterwards. It also
plants a latent pass/fail on every trace at the Chapter 2 first-pass rates, so
sampling strategies can be scored against a known answer. Nothing was tuned
after a run. Output: out/trace_store.db and out/truth.json.
"""
import json
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "truss"))
from truss.complete import REQUIRED_TOOLS  # noqa: E402
from truss.redact import Redactor  # noqa: E402
from truss.store import open_store  # noqa: E402
from truss.tracestore import create_store, write_trace  # noqa: E402

SEED = 2026
OUT = HERE / "out"
STORE = OUT / "trace_store.db"
# Chapter 2 first-pass failure rates by flow (fails / sampled).
BASE_FAIL = {"account_question": 3 / 40, "fee_explanation": 6 / 70, "statement_request": 1 / 25,
             "payoff_letter": 3 / 35, "lien_release": 3 / 30, "hardship": 11 / 100}
MODES = {
    "hardship": [("offer drafted before income confirmed", 6),
                 ("no hand-off when borrower asked for a person", 3),
                 ("offer sent without saying a loan officer must approve it", 2)],
    "fee_explanation": [("ten-day grace period quoted (policy is 15)", 4),
                        ("fee not waived when policy says waive", 2)],
    "account_question": [("wrong balance date", 2), ("missed borrower's second loan", 1)],
    "payoff_letter": [("per diem interest omitted", 2), ("wrong good-through date", 1)],
    "lien_release": [("release promised before title office date", 2), ("wrong title state", 1)],
    "statement_request": [("wrong statement period", 1)],
}
MEAN_TURNS = {"account_question": 3.6, "fee_explanation": 6.5, "statement_request": 3.6,
              "payoff_letter": 5.5, "lien_release": 7.6, "hardship": 13.5}
STATES = [("AZ", 46), ("NV", 16), ("NM", 9), ("TX", 21), ("CO", 8)]
TITLE_LAG = {"AZ": (6, 13), "NV": (8, 16), "NM": (10, 21), "TX": (7, 15), "CO": (12, 26)}
FIRST = ["Maria", "James", "Ana", "David", "Linda", "Jose", "Karen", "Luis", "Emily", "Robert",
         "Sofia", "Daniel", "Grace", "Miguel", "Laura", "Kevin", "Rosa", "Brian", "Elena", "Tom"]
LAST = ["Lopez", "Nguyen", "Carter", "Garcia", "Patel", "Brooks", "Reyes", "Kim", "Silva", "Ward"]
N_BORROWERS = 17_800
EXTRACT = "2026-10-25T00:00:00"   # when the outcome feeds were pulled for the pilot


def reached_offer(trace_id):          # same rule as Chapter 2
    return random.Random(f"offer|{trace_id}").random() < 0.64


def money(x):
    return f"${x:,.2f}"


def borrower(b):
    r = random.Random(f"borrower|{b}")
    st = r.choices([s for s, _ in STATES], [w for _, w in STATES])[0]
    loans = []
    for k in range(2 if r.random() < 0.09 else 1):
        amt = min(48_000, max(6_000, math.exp(r.gauss(9.85, 0.45))))
        loans.append({"loan": f"L{b:05d}{k}", "amount": round(amt, 2),
                      "payment": round(amt * 0.0203, 2), "last4": f"{r.randrange(10000):04d}",
                      "acct": f"{r.randrange(10**9, 10**10)}"})
    name = f"{r.choice(FIRST)} {r.choice(LAST)}"
    return {"b": b, "state": st, "loans": loans, "name": name,
            "phone": f"({r.randrange(480, 929)}) {r.randrange(200, 999)}-{r.randrange(10000):04d}",
            "email": f"{name.split()[0].lower()}{b}@example.com",
            "income": r.choice([1800, 2200, 2600, 2900, 3400, 4100]),
            "prior_deferral": "2026-03-%02d" % r.randrange(2, 28) if r.random() < 0.09 else None}


def evidence(flow, bw, loan, r, fail_mode, started):
    d = started[:10]
    if flow == "account_question":
        return {"balance": money(loan["amount"] * r.uniform(0.35, 0.95)), "as_of": d}
    if flow == "fee_explanation":
        grace_fail = bool(fail_mode and "ten-day" in fail_mode)
        stale = grace_fail or r.random() < 0.01
        # The servicing system returns the right grace period; the retrieved policy
        # document is what can be stale. Its version lives on the retrieval span.
        return {"fee_amount": "$25.00", "days_late": r.randrange(11, 15) if grace_fail else r.randrange(3, 20),
                "grace_days": 15, "schedule_version": "fee-schedule-2024-01" if stale else "fee-schedule-2026-03"}
    if flow == "statement_request":
        return {"period": "September 2026" if d >= "2026-10-01" else "August 2026"}
    if flow == "payoff_letter":
        bal = loan["amount"] * r.uniform(0.2, 0.8)
        return {"payoff_amount": money(bal), "good_through": d,
                "per_diem": money(bal * 0.0795 / 365)}
    if flow == "lien_release":
        return {"paid_in_full_on": d, "title_state": bw["state"]}
    return {"loan_amount": money(loan["amount"]), "monthly_payment": money(loan["payment"]),
            "stated_income": f"${bw['income']:,} a month", "prior_deferral_on": bw["prior_deferral"],
            "policy_version": "hardship-policy-2026-06"}


def build():
    OUT.mkdir(exist_ok=True)
    if STORE.exists():
        STORE.unlink()
    for ext in ("-wal", "-shm"):
        Path(str(STORE) + ext).unlink(missing_ok=True)
    src = open_store()
    rows = src.execute("SELECT trace_id, started_at, channel, flow, risk_tier, turns "
                       "FROM traces ORDER BY trace_id").fetchall()
    red = Redactor()
    db = create_store(STORE)
    truth = {"fail": {}, "mode": {}, "links": {}, "complaints": [], "incidents": {}}
    outcomes_all = []
    flow_fail_ids = {f: [] for f in BASE_FAIL}
    for tid, started, channel, flow, tier, turns in rows:
        r = random.Random(f"v05|{tid}")
        b = int(N_BORROWERS * r.random() ** 1.15)
        bw = borrower(b)
        loan = r.choice(bw["loans"])
        utc = (datetime.fromisoformat(started) + timedelta(hours=7)).isoformat()
        p = min(0.6, BASE_FAIL[flow] * (turns / MEAN_TURNS[flow]) ** 0.9)
        failed = r.random() < p
        modes = MODES[flow]
        mode = r.choices([m for m, _ in modes], [k for _, k in modes])[0] if failed else None
        offer = flow == "hardship" and reached_offer(tid)
        if mode and "offer" in mode and not offer:
            mode = "no hand-off when borrower asked for a person"
        ev = evidence(flow, bw, loan, r, mode, utc)
        prompt = "compass-prompt-v3"   # one prompt version for the whole pilot (Chapter 2)
        trace = {"trace_id": tid, "conversation_id": "conv_" + tid[2:], "schema_version": "0.5",
                 "started_at_utc": utc, "channel": channel, "flow": flow, "risk_tier": tier,
                 "turns": turns, "router_version": "router-1.2", "model_id": "compass-llm-2026-08",
                 "temperature": 0.7, "prompt_version": prompt,
                 "policy_corpus_version": "policy-2026-09-01",
                 "borrower_token": red.token("borrower", bw["b"]),
                 "loan_token": red.token("loan", loan["loan"]), "state": bw["state"],
                 "ingested_at_utc": utc}
        spans, seq = [], 0

        def span(kind, name, attrs, parent="s0"):
            nonlocal seq
            spans.append({"span_id": f"{tid}.s{seq}", "parent_id": None if seq == 0 else f"{tid}.{parent}",
                          "kind": kind, "name": name, "seq": seq, "attrs": attrs})
            seq += 1
        span("invoke_agent", "invoke_agent compass", {"agent_name": "compass"})
        span("chat", "chat router", {"model_id": "router-1.2", "input": "[first message]",
                                     "output": flow, "input_tokens": 180, "output_tokens": 4,
                                     "latency_ms": r.randrange(90, 260)})
        tools = list(REQUIRED_TOOLS[flow]) + (["send_letter"] if flow == "payoff_letter" else [])
        if flow == "hardship":
            tools += ["check_hardship_eligibility"] + (["draft_offer"] if offer else [])
        for i in range(turns):
            if i == 0:
                hello = f"Hi, this is {bw['name']}. " if r.random() < 0.3 else ""
                extra = ""
                if r.random() < 0.04:
                    extra = f" You can call me on {bw['phone']}."
                if r.random() < 0.004:
                    extra += f" My social is {r.randrange(100,999)} {r.randrange(10,99)} {r.randrange(1000,9999)}."
                text = red.text(hello + f"Question about loan ending {loan['last4']}.{extra}", names=[bw["name"]])
            else:
                text = "[borrower turn]"
            span("chat", "chat compass-llm-2026-08",
                 {"model_id": "compass-llm-2026-08", "input": text, "output": "[reply]",
                  "input_tokens": 900 + 160 * i, "output_tokens": r.randrange(40, 160),
                  "latency_ms": r.randrange(700, 2600)})
            if i == 0:
                for tname in tools:
                    res = {k: v for k, v in ev.items() if k != "schedule_version"} if tname != "get_account" else {
                        "balance": money(loan["amount"] * 0.7), "loan_token": trace["loan_token"]}
                    if tname == "get_account_history":
                        res = {"prior_deferral_on": bw["prior_deferral"]}
                    if tname == "send_letter":   # the document service renders the letter later
                        res = {"letter_id": f"LTR-{tid[2:]}", "status": "queued"}
                    span("execute_tool", f"execute_tool {tname}",
                         {"tool_name": tname, "call_id": f"call_{tid[2:]}_{tname}",
                          "arguments": {"loan_token": trace["loan_token"]}, "result": res,
                          "status": "ok", "latency_ms": r.randrange(60, 900)})
                if flow in ("fee_explanation", "hardship"):
                    ver = ev.get("schedule_version", ev.get("policy_version"))
                    span("retrieve", "execute_tool retrieve_policy",
                         {"query": flow.replace("_", " "), "doc_ids": [ver.rsplit("-", 2)[0]],
                          "doc_versions": [ver]})
        if r.random() < (0.45 if flow == "hardship" else 0.27):
            span("handoff", "execute_tool handoff", {"reason": "borrower asked" if r.random() < .6 else "policy",
                                                    "queue": "loan-officers" if flow == "hardship" else "servicing"})
        outs = []
        t0 = datetime.fromisoformat(utc)

        def outcome(kind, at, value, source, true_trace, direct=None):
            oid = f"o-{tid[2:]}-{len(outs)}"
            o = {"outcome_id": oid, "trace_id": direct, "borrower_token": trace["borrower_token"],
                 "loan_token": trace["loan_token"], "kind": kind, "occurred_at_utc": at.isoformat(),
                 "value": value, "source": source}
            outs.append(o)
            if true_trace:
                truth["links"][oid] = true_trace
        if r.random() < (0.27 if failed else 0.09):
            outcome("recontact_call", t0 + timedelta(days=r.uniform(0.2, 6.5)), "called about same issue",
                    "contact_centre", tid)
        if r.random() < 0.05:   # an unrelated call by the same borrower
            outcome("recontact_call", t0 + timedelta(days=r.uniform(-9, 9)), "unrelated call",
                    "contact_centre", None)
        if offer:
            dec = r.choices(["approved", "edited", "rejected"], [83, 11, 6])[0]
            outcome("officer_decision", t0 + timedelta(days=r.uniform(0.2, 3)), dec, "servicing", tid,
                    direct=tid)
        if flow == "lien_release":
            lo, hi = TITLE_LAG[bw["state"]]
            at = t0 + timedelta(days=r.randrange(lo, hi + 1))
            truth.setdefault("title_lag", {})[tid] = (at - t0).days
            if at.isoformat() <= EXTRACT:
                outcome("title_recorded", at, bw["state"], "title_office", tid)
        write_trace(db, trace, spans, outs)
        outcomes_all += outs
        truth["fail"][tid] = failed
        if mode:
            truth["mode"][tid] = mode
            flow_fail_ids[flow].append(tid)
    # Complaints (14 in six weeks): picked among failed traces by planned flow counts.
    rng = random.Random(SEED)
    plan = {"fee_explanation": 3, "hardship": 1, "account_question": 3, "payoff_letter": 3,
            "lien_release": 2, "statement_request": 2}
    for flow, k in plan.items():
        pool = [t for t in flow_fail_ids[flow] if
                (flow != "fee_explanation" or "ten-day" in truth["mode"][t])
                and (flow != "lien_release" or truth.get("title_lag", {}).get(t, 0) > 14)]
        if flow == "hardship":   # the offer the policy did not permit: a second deferral
            pool = [t for t, in db.execute(
                "SELECT t.trace_id FROM traces t JOIN spans s ON s.trace_id=t.trace_id "
                "WHERE t.flow='hardship' AND s.name='execute_tool draft_offer'")]
            pool = [t for t in pool if json.loads(db.execute(
                "SELECT attrs FROM spans WHERE trace_id=? AND name='execute_tool get_account_history'",
                (t,)).fetchone()[0])["result"]["prior_deferral_on"]]
        for t in sorted(rng.sample(sorted(pool), k)):
            if flow == "hardship":
                truth["fail"][t] = True
                truth["mode"][t] = "second deferral within 12 months offered"
            at = datetime.fromisoformat(db.execute("SELECT started_at_utc FROM traces WHERE trace_id=?",
                                                   (t,)).fetchone()[0]) + timedelta(days=rng.uniform(1, 12))
            bt, lt = db.execute("SELECT borrower_token, loan_token FROM traces WHERE trace_id=?", (t,)).fetchone()
            oid = f"c-{t[2:]}"
            db.execute("INSERT INTO outcomes VALUES (?,?,?,?,?,?,?,?)",
                       (oid, None, bt, lt, "complaint", at.isoformat(), flow, "complaints"))
            truth["links"][oid] = t
            truth["complaints"].append(t)
    db.commit()
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.close()
    json.dump(truth, open(OUT / "truth.json", "w"))
    return truth


if __name__ == "__main__":
    t = build()
    print(f"built {STORE.name}: {len(t['fail'])} traces, {len(t['complaints'])} complaints")
