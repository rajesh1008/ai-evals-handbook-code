"""Shared loaders for the Chapter 3 Lab."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "truss"))
from truss.store import open_store  # noqa: E402

OUT = HERE / "out"
STORE = OUT / "trace_store.db"
ORDER = ["account_question", "fee_explanation", "statement_request",
         "payoff_letter", "lien_release", "hardship"]
SHARES = {"account_question": .415, "fee_explanation": .215, "statement_request": .143,
          "payoff_letter": .108, "lien_release": .060, "hardship": .059}
QUOTAS = {"hardship": 100, "fee_explanation": 70, "account_question": 40,
          "payoff_letter": 35, "lien_release": 30, "statement_request": 25}


def db():
    if not STORE.exists():
        import build_store
        build_store.build()
    return open_store(STORE)


def truth():
    return json.load(open(OUT / "truth.json"))


def frame(con):
    hand = {t for t, in con.execute("SELECT trace_id FROM spans WHERE kind='handoff'")}
    return [{"trace_id": t, "flow": f, "risk_tier": r, "turns": n, "channel": c,
             "started_at_utc": s, "borrower_token": b, "loan_token": lt, "state": st,
             "prompt_version": pv, "handoff": t in hand}
            for t, f, r, n, c, s, b, lt, st, pv in con.execute(
                "SELECT trace_id, flow, risk_tier, turns, channel, started_at_utc, borrower_token, "
                "loan_token, state, prompt_version FROM traces ORDER BY trace_id")]


def evidence_by_trace(con):
    """The flow's evidence, as the tool results on the trace record it."""
    from truss.schema import EVIDENCE
    ev = {}
    for t, f, a in con.execute("SELECT s.trace_id, t.flow, s.attrs FROM spans s JOIN traces t "
                               "USING(trace_id) WHERE s.kind='execute_tool'"):
        res = json.loads(a)["result"]
        cur = ev.setdefault(t, {"flow": f})
        for k in EVIDENCE[f]:
            if k in res and k not in cur:
                cur[k] = res[k]
    for t, a in con.execute("SELECT trace_id, attrs FROM spans WHERE kind='retrieve'"):
        v = json.loads(a)["doc_versions"][0]
        if v.startswith("fee-schedule"):
            ev[t]["schedule_version"] = v
    return ev


def save(name, obj):
    json.dump(obj, open(OUT / f"{name}.json", "w"), indent=1)
