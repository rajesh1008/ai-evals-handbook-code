"""Chapter 4: every Truss check Harbor Lending runs, tagged with a layer,
a stream, an owner, the stages it runs at, and a cost per item."""
import json
import sys
from datetime import date

import harbor as H
from truss.complete import missing_tools
from truss.gate import decide
from truss.layers import Check, Cost, Suite
from truss.redact import Redactor, evidence_report
from truss.sampling import frame_hash, verify
from truss.schema import gaps

sys.path.insert(0, str(H.ROOT / "ch01"))
from replay import check_manifest  # noqa: E402

LATENCY_BUDGET_S = 5.0
PEAK_TURNS_PER_MIN = {"pilot": 7, "full": 70}   # reply turns a minute in the Monday-morning peak hour


def ctx_for(defects=(), con=None):
    con = con or H.store()
    sample, frame = H.gate_sample(con)
    return {"defects": tuple(defects), "con": con, "sample": sample, "frame": frame,
            "docs": H.corpus(defects), "tok": H.tokens_by_flow(con)}


def build(tok):
    S = Suite(H.PRICES)
    ryan, lead, comp = "Ryan (engineering)", "evaluation lead", "Victor (compliance) rules, Ryan code"
    fast = Cost(cpu_seconds=0.01)

    # ---------------- layer 1: deterministic code, every commit
    @S.check("router wrapper parses labels", 1, "code tests", ryan, ("commit", "pull_request", "release"), fast)
    def _(ctx):
        cases = {"payoff_letter": "payoff_letter", "Hardship": "hardship", "fee explanation": "fee_explanation",
                 "refund": "handoff", "": "handoff"}
        bad = [k for k, v in cases.items() if H.parse_router(k) != v]
        return len(cases), len(bad), f"failing inputs {bad}" if bad else ""

    @S.check("tool requests carry a loan token", 1, "code tests", ryan, ("commit", "pull_request", "release"), fast)
    def _(ctx):
        reqs = [{"tool": t, "arguments": {"loan_token": "LOAN_x"}} for t in
                ("get_account", "get_fee_schedule", "get_payoff_quote", "get_title_status", "draft_offer")]
        bad = [r for r in reqs if not r["arguments"].get("loan_token")]
        return len(reqs), len(bad), ""

    @S.check("replies fit three SMS parts", 1, "code tests", ryan, ("commit", "pull_request", "release"), fast)
    def _(ctx):
        replies = ["Your late fee is $25.00 because your payment arrived 16 days after the due date. "
                   "Our grace period is 15 days.", "A loan officer must approve this offer before it applies."]
        bad = [x for x in replies if H.sms_parts(x) > 3]
        return len(replies), len(bad), ""

    @S.check("fee rule at the grace boundary", 1, "code tests", comp, ("commit", "pull_request", "release"), fast)
    def _(ctx):
        want = {11: False, 14: False, 15: False, 16: True, 30: True}
        bad = [d for d, w in want.items() if H.fee_applies(d, 15, ctx["defects"]) != w]
        return len(want), len(bad), f"wrong at days late {bad}" if bad else ""

    @S.check("second deferral within twelve months refused", 1, "code tests", comp,
             ("commit", "pull_request", "release"), fast)
    def _(ctx):
        want = {("2026-03-12", "2026-12-14"): True, ("2025-12-14", "2026-12-14"): False,
                ("2025-12-15", "2026-12-14"): True, (None, "2026-12-14"): False}
        bad = [k for k, w in want.items() if H.second_deferral_blocked(*k) != w]
        return len(want), len(bad), ""

    @S.check("no retired document in the policy index", 1, "code tests", comp,
             ("commit", "pull_request", "release"), fast)
    def _(ctx):
        stale = [d["version"] for d in ctx["docs"] if d["retired_on"] and d["retired_on"] <= H.TODAY]
        return len(ctx["docs"]), len(stale), f"retired but indexed: {stale}" if stale else ""

    @S.check("redaction keeps the evidence a reader needs", 1, "code tests", "privacy team + evaluation lead",
             ("commit", "pull_request", "release"), fast)
    def _(ctx):
        cases = [("hardship", {"prior_deferral_on": "2026-03-09", "loan_amount": "$8,298.77",
                               "monthly_payment": "$168.46", "stated_income": "$3,400 a month",
                               "policy_version": "hardship-policy-2026-06"}),
                 ("fee_explanation", {"fee_amount": "$25.00", "days_late": 12, "grace_days": 15})]
        rep = evidence_report(Redactor(), cases)
        lost = sum(n - k for k, n in rep.values())
        return len(cases), lost, ""

    @S.check("replayed traces are complete", 1, "code tests", lead, ("release",), fast)
    def _(ctx):
        ids = [t for t, _ in ctx["sample"]]
        q = ("SELECT t.trace_id, t.flow, group_concat(json_extract(s.attrs,'$.tool_name')) FROM traces t "
             "JOIN spans s USING(trace_id) WHERE s.kind='execute_tool' AND t.trace_id IN (%s) GROUP BY 1"
             % ",".join("?" * len(ids)))
        bad = [t for t, f, tools in ctx["con"].execute(q, ids) if missing_tools(f, (tools or "").split(","))]
        return len(ids), len(bad), ""

    @S.check("replayed traces meet the v0.5 contract", 1, "code tests", lead, ("release",), fast)
    def _(ctx):
        ids = [t for t, _ in ctx["sample"]]
        con, bad = ctx["con"], 0
        cols = [d[1] for d in con.execute("PRAGMA table_info(traces)")]
        for t in ids:
            tr = dict(zip(cols, con.execute("SELECT * FROM traces WHERE trace_id=?", (t,)).fetchone()))
            spans = [{"kind": k, "name": n, "attrs": json.loads(a)} for k, n, a in
                     con.execute("SELECT kind, name, attrs FROM spans WHERE trace_id=?", (t,))]
            bad += bool(gaps(tr, spans))
        return len(ids), bad, ""

    @S.check("sample manifest matches its frame", 1, "code tests", lead, ("release",), fast)
    def _(ctx):
        ids = [r["trace_id"] for r in ctx["frame"]]
        m = {"sample_id": "first-pass-2026-10", "frame_count": len(ids), "frame_sha256": frame_hash(ids)}
        try:
            verify(m, ids)
            return 1, 0, ""
        except ValueError as e:
            return 1, 1, str(e)

    @S.check("candidate runs share one temperature", 1, "code tests", lead, ("release",), fast)
    def _(ctx):
        runs = {"t1": [{"temperature": 0.3}], "t2": [{"temperature": 0.3}]}
        try:
            check_manifest(runs)
            return 2, 0, ""
        except ValueError as e:
            return 2, 1, str(e)

    # layer 1 run on production traces each week: deterministic code, online data
    @S.check("traces that retrieved a retired document", 1, "code tests", lead, ("weekly",), fast)
    def _(ctx):
        rows = ctx["con"].execute("SELECT trace_id, attrs FROM spans WHERE kind='retrieve'").fetchall()
        bad = [t for t, a in rows if set(json.loads(a)["doc_versions"]) & H.RETIRED]
        ctx["retired_hits"] = bad
        return len(rows), len(bad), ""

    # ---------------- layer 2: model components on labelled fixtures, every pull request
    @S.check("router recall on 600 labelled first messages", 2, "component evals", "Ryan + data science",
             ("pull_request", "release"), Cost(input_tokens=180, output_tokens=4))
    def _(ctx):
        fx = H.router_fixture()
        got = {m["id"]: H.route_model(m, ctx["defects"]) for m in fx}
        rec = {}
        for f in H.FLOWS:
            rows = [m for m in fx if m["label"] == f]
            rec[f] = sum(got[m["id"]] == f for m in rows) / len(rows)
        ctx["router_recall"] = rec
        low = [f for f, v in rec.items() if v < (0.95 if f == "hardship" else 0.90)]
        return len(fx), len(low), "recall " + ", ".join(f"{f} {v:.2f}" for f, v in rec.items())

    @S.check("retrieval returns the current version", 2, "component evals", "Ryan + loan officers (labels)",
             ("pull_request", "release"), Cost(input_tokens=400, output_tokens=0))
    def _(ctx):
        fx = H.retrieval_fixture()
        wrong = [q for q in fx if H.retrieve(q, ctx["docs"], ctx["defects"]) != q["label"]]
        return len(fx), len(wrong), ""

    # ---------------- layer 3: task evals on the sampled, replayed traces, every release
    hs, ot = tok["hardship"], {f: tok[f] for f in H.FLOWS if f != "hardship"}
    other_in = sum(ot[f]["in"] * H.QUOTAS[f] for f in ot) / 200
    other_out = sum(ot[f]["out"] * H.QUOTAS[f] for f in ot) / 200

    @S.check("hardship traces read by loan officers", 3, "human review", "Grace (loan officers)", ("release",),
             Cost(hs["in"], hs["out"], human_minutes=10, human_rate=H.OFFICER_RATE))
    def _(ctx):
        ids = [t for t, _ in ctx["sample"] if t in ctx["hardship_ids"]]
        base, cand = H.hardship_replay(ids), H.hardship_replay(ids, ctx["defects"])
        newly = sum(base[t] == "pass" and cand[t] == "fail" for t in ids)
        ctx["changes"] = {"hardship": (newly, 0)}
        return len(ids), newly, f"{newly} newly fail"

    @S.check("other flows read by the evaluation lead", 3, "human review", lead, ("release",),
             Cost(other_in, other_out, human_minutes=3, human_rate=H.LEAD_RATE))
    def _(ctx):
        return 200, 0, ""

    @S.check("Gate v0 decision", 3, "statistics", "Sarah (override)", ("release",), Cost())
    def _(ctx):
        verdict, reasons = decide(True, 0, ctx.get("changes", {}), 0)
        return 1, int(verdict == "hold"), "; ".join(reasons)

    # ---------------- layer 4: trajectories with simulated borrowers, every release
    per_turn_in, per_turn_out = hs["in"] / 13.5 + 1200, hs["out"] / 13.5 + 60   # Compass + simulator

    @S.check("simulated hardship borrowers resolve", 4, "judge evals", "evaluation lead + Ryan", ("release",),
             Cost(per_turn_in * 14, per_turn_out * 14))
    def _(ctx):
        runs = [H.simulate(s, ctx["defects"]) for s in H.scenarios() for _ in range(3)]
        stuck = [r for r in runs if not r["resolved"]]
        return len(runs), len(stuck), f"{len(stuck)} of {len(runs)} hit the 30-turn cap"

    @S.check("staging latency at pilot peak", 4, "code tests", "Sarah (platform)", ("release",), Cost(cpu_seconds=0.5))
    def _(ctx):
        extra = 1.8 if "reranker_slow" in ctx["defects"] else 0.0
        p95 = H.latency_p95(PEAK_TURNS_PER_MIN["pilot"], extra_retrieval_s=extra)
        return 1, int(p95 > LATENCY_BUDGET_S), f"p95 {p95:.1f} s"

    # ---------------- layer 5: shadow and online, before widening and weekly
    mean_conv = sum(H.SHARES[f] * H.conv_dollars(tok[f]) for f in H.FLOWS)
    ctx_mean = sum(H.SHARES[f] * tok[f]["in"] for f in H.FLOWS), sum(H.SHARES[f] * tok[f]["out"] for f in H.FLOWS)

    @S.check("shadow week at full volume", 5, "online", "Sarah (platform) + evaluation lead", ("shadow",),
             Cost(*ctx_mean))
    def _(ctx):
        extra = 1.8 if "reranker_slow" in ctx["defects"] else 0.0
        p95 = H.latency_p95(PEAK_TURNS_PER_MIN["full"], extra_retrieval_s=extra)
        return 5700 * 7, int(p95 > LATENCY_BUDGET_S), f"peak p95 {p95:.1f} s"

    @S.check("weekly monitoring sample", 5, "human review", "evaluation lead", ("weekly",),
             Cost(human_minutes=440 / 70 / H.LEAD_RATE * 60, human_rate=H.LEAD_RATE))
    def _(ctx):
        return 70, 0, ""

    @S.check("complaints linked to traces", 5, "online", "Rachel (reads outcomes)", ("weekly",), Cost())
    def _(ctx):
        n = ctx["con"].execute("SELECT COUNT(*) FROM outcomes WHERE kind='complaint'").fetchone()[0]
        return n, 0, f"{n} complaints in the pilot"

    S.mean_conv = mean_conv
    return S


def hardship_ids(con):
    return {t for t, in con.execute("SELECT trace_id FROM traces WHERE flow='hardship'")}
