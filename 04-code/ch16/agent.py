"""Chapter 16, REAL model run: agent-as-a-judge. The judge gets two read-only sandbox tools over the
servicing-core snapshot (SIMULATED records from fixture.py) and the MC-02 v1.2 question, which adds the
account record and fee schedule to what the reply is compared against. Run: python3 agent.py run"""
import concurrent.futures as cf
import json
import random
import sys
import time

import fixture as F
import gen
import judges as J
import llm

SCHEDULE = ("fee-schedule-2026-03: late fee $25 when a payment posts more than 15 days after the due date. "
            "Courtesy waiver: one late fee waived in any rolling twelve months (365 days before the fee date) for "
            "borrowers enrolled in autopay, applied without a call. An open waiver request is decided by a loan officer.")
TOOLS = [
    {"name": "get_account_history", "description": "Read-only. Servicing-core events for one loan: payments due and posted, fees, courtesy waivers, autopay enrolment, waiver requests.",
     "input_schema": {"type": "object", "properties": {"loan": {"type": "string", "description": "last four digits"}}, "required": ["loan"]}},
    {"name": "get_fee_schedule", "description": "Read-only. The fee schedule in force.",
     "input_schema": {"type": "object", "properties": {}}},
]
DAYS_TOOL = {"name": "days_between", "description": "Exact number of days from one ISO date to a later one.",
             "input_schema": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}},
                              "required": ["start", "end"]}}
CARD_Q12 = ("Did the reply state a fee amount, grace period or waiver status that differs from what the fee tool "
            "returned, or would have returned, for the loan the borrower named, or from what that loan's account "
            "record and the fee schedule in force say?")
PROMPT = """You are checking one reply from Compass, Harbor Lending's loan-servicing assistant. This is check MC-02 v1.2 (wrong fee explanation).

Question: {q}

You can read the account record and the fee schedule with your tools. Use them: check the facts the reply states against the record for the loan the borrower named and against the schedule, not only against the fee tool's span. The fee tool can be wrong; if its result conflicts with the record and schedule, the record and schedule decide. Tone and style are not part of this check. Use cannot_tell only if you cannot get what you need.

Trace date: {date}
{trace}

When you are done, write a critique of at most four sentences, then on the last line output JSON only: {{"verdict": "pass" | "fail" | "cannot_tell"}}"""


def other_record(t):
    g = random.Random("other-" + t["trace_id"])
    d = F.date.fromisoformat(t["date"])
    w = d - F.timedelta(days=g.randint(60, 200))
    return {"loan": t["other"], "autopay": True, "events": [
        {"date": F.ymd(d - F.timedelta(days=900)), "event": "autopay_enrolled"},
        {"date": F.ymd(w), "event": "courtesy_waiver_applied", "amount": 25}]}


def tool_result(t, name, args):
    if name == "get_fee_schedule":
        return SCHEDULE
    if name == "days_between":
        try:
            return str((F.date.fromisoformat(args["end"]) - F.date.fromisoformat(args["start"])).days)
        except (KeyError, ValueError):
            return "error: dates must be YYYY-MM-DD"
    loan = str(args.get("loan", "")).strip()[-4:]
    if loan == t["asked"]:
        h = t["history"]
        return json.dumps({"loan": h["loan"], "autopay": h["autopay"], "events": h["events"]})
    if loan == t["other"]:
        return json.dumps(other_record(t))
    return json.dumps({"error": f"no loan ending {loan} for this borrower"})


def run_one(t, reply, model, max_turns=6, tools=TOOLS):
    """Agent loop: each messages.create is budget-reserved independently (global $12 ledger)."""
    import anthropic
    import budget as B
    B.assert_model_priced(model)
    # No unbounded SDK retries; each attempt must re-reserve under the hard cap.
    client = anthropic.Anthropic(max_retries=0, timeout=180.0)
    msgs = [{"role": "user", "content": PROMPT.format(q=CARD_Q12, date=t["date"], trace=J.block(t, reply))}]
    tin = tout = 0; calls = []; t0 = time.perf_counter(); text = ""; last_model = model
    request_ids = []
    for turn in range(max_turns):
        req = {"model": model, "max_tokens": 1200, "tools": tools, "messages": msgs}
        rid = None
        if B.enabled():
            worst = B.worst_case_usd(req)
            try:
                rid = B.get_ledger().reserve(worst, meta={"tag": "agent", "item": t["trace_id"],
                                                          "turn": turn, "model": model})
            except B.BudgetExhausted:
                # Stop this trace cleanly; partial tool trail preserved.
                break
        try:
            m = client.messages.create(**req)
        except Exception as e:
            if rid is not None:
                name = type(e).__name__
                if name in ("APIConnectionError", "APITimeoutError") or "connection" in str(e).lower():
                    B.get_ledger().release(rid, reason=f"likely_uncharged:{name}")
                else:
                    B.get_ledger().mark_unreconciled(rid, f"{name}: {e}")
            raise
        last_model = m.model
        request_ids.append(getattr(m, "id", None))
        tin += m.usage.input_tokens; tout += m.usage.output_tokens
        if rid is not None:
            B.get_ledger().commit(rid, B.guarded_cost_usd(m.model, m.usage.input_tokens, m.usage.output_tokens))
        text = "".join(b.text for b in m.content if b.type == "text").strip()
        uses = [b for b in m.content if b.type == "tool_use"]
        if not uses:
            break
        msgs.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in m.content]})
        res = []
        for u in uses:
            calls.append({"name": u.name, "input": u.input})
            res.append({"type": "tool_result", "tool_use_id": u.id, "content": tool_result(t, u.name, u.input)})
        msgs.append({"role": "user", "content": res})
    return {"text": text, "model": last_model, "in": tin, "out": tout,
            "latency": round(time.perf_counter() - t0, 3), "tool_calls": calls,
            "request_ids": request_ids, "cost_usd": B.guarded_cost_usd(last_model, tin, tout) if tin or tout else 0.0}


def run(model, live=False, calc=False):
    bugs, normal = F.agent_set()
    R = gen.replies()
    tag = "agent_" + ("large" if model == llm.LARGE else "small") + ("_calc" if calc else "")
    tools = TOOLS + [DAYS_TOOL] if calc else TOOLS
    path = llm.OUT / f"{tag}.jsonl"
    done = {}
    if path.exists():
        done = {r["item"]: r for r in map(json.loads, path.read_text().splitlines())}
    todo = [t for t in bugs + normal if t["trace_id"] not in done]
    if todo and live:
        print(f"  [{tag}] running {len(todo)} agent judgements")
        with path.open("a") as fh, cf.ThreadPoolExecutor(6) as ex:
            futs = {ex.submit(run_one, t, R[t["trace_id"]]["text"], model, 6, tools): t for t in todo}
            for f in cf.as_completed(futs):
                t = futs[f]
                try:
                    rec = f.result()
                except Exception as e:
                    import budget as B
                    if isinstance(e, B.BudgetExhausted):
                        print(f"  [{tag}] BUDGET STOP at {t['trace_id']}: {e}")
                        for other in futs:
                            other.cancel()
                        break
                    print(f"  [{tag}] {t['trace_id']}: {type(e).__name__}"); continue
                rec["item"] = t["trace_id"]
                fh.write(json.dumps(rec) + "\n"); fh.flush()
                done[t["trace_id"]] = rec
    return done


if __name__ == "__main__":
    live = sys.argv[1:] == ["run"]
    for m, calc in ((llm.SMALL, False), (llm.LARGE, False), (llm.SMALL, True)):
        d = run(m, live, calc)
        u = llm.usage(d.values())
        print(f"agent {m}{' + days_between' if calc else ''}: {len(d)} traces, {sum(len(r['tool_calls']) for r in d.values())} tool calls, ${u['cost']:.3f}")
