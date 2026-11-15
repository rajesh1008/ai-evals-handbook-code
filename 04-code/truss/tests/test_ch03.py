"""Chapter 3: trace contract, redaction, trace store, sampling, outcomes."""
import re
import sqlite3

import pytest

from truss import sampling as S
from truss.outcomes import link_fuzzy, matured, score_links
from truss.redact import Redactor, evidence_report, residual
from truss.schema import EVIDENCE, gaps, to_otel
from truss.store import open_store
from truss.tracestore import create_store, ddl, write_trace


def test_gaps_names_missing_fields():
    tr = {"trace_id": "t1", "flow": "fee_explanation"}
    g = gaps(tr, [{"kind": "execute_tool", "name": "get_fee_schedule", "attrs": {"tool_name": "x"}}])
    assert "trace.prompt_version" in g and "execute_tool:get_fee_schedule.result" in g


def test_otel_mapping():
    o = to_otel({"kind": "execute_tool", "attrs": {"tool_name": "get_account", "call_id": "c1", "result": {}}})
    assert o["name"] == "execute_tool get_account"
    assert o["gen_ai.operation.name"] == "execute_tool" and o["gen_ai.tool.call.id"] == "c1"


def test_tokens_stable_and_evidence_kept():
    r = Redactor()
    assert r.token("borrower", 17) == r.token("borrower", 17) != r.token("borrower", 18)
    s = r.text("Hi, this is Ana Silva, call (602) 555-0142 about $14,382.10", names=["Ana Silva"])
    assert "Ana" not in s and "555" not in s and "$14,382.10" in s
    assert residual("my social is 123 45 6789") == ["123 45 6789"]


def test_amount_rule_fails_evidence_check():
    ev = {"flow": "hardship", "loan_amount": "$8,298.77", "monthly_payment": "$168.46",
          "stated_income": "$3,400 a month", "prior_deferral_on": None, "policy_version": "p"}
    assert evidence_report(Redactor(), [("hardship", ev)]) == {"hardship": (1, 1)}
    bad = Redactor(extra_rules={"amt": re.compile(r"\$\d{1,3}(?:,\d{3})+(?:\.\d{2})?")})
    assert evidence_report(bad, [("hardship", ev)]) == {"hardship": (0, 1)}
    assert set(EVIDENCE) == {"account_question", "fee_explanation", "statement_request",
                             "payoff_letter", "lien_release", "hardship"}


def test_store_appends_and_refuses_overwrite(tmp_path):
    p = tmp_path / "s.db"
    db = create_store(p)
    t = {"trace_id": "t1", "flow": "hardship"}
    write_trace(db, t, [{"span_id": "t1.s0", "kind": "invoke_agent", "name": "a", "seq": 0, "attrs": {}}])
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        write_trace(db, t, [])
    ro = open_store(p)
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("DELETE FROM traces")
    assert any("JSONB" in s for s in ddl("postgres")) and any("TIMESTAMPTZ" in s for s in ddl("postgres"))


FRAME = [{"trace_id": f"t{i:04d}", "flow": "h" if i % 10 == 0 else "a", "risk": 5 if i % 10 == 0 else 1}
         for i in range(2000)]


def test_strategies_and_weights():
    u = S.uniform(FRAME, 100)
    assert len(u) == 100 and u == S.uniform(FRAME, 100)
    st = S.stratified(FRAME, "flow", {"h": 50, "a": 50})
    assert sum(w for _, w in st) == pytest.approx(2000)
    p = S.inclusion_probs({r["trace_id"]: r["risk"] for r in FRAME}, 100)
    assert sum(p.values()) == pytest.approx(100) and max(p.values()) <= 1
    fail = {r["trace_id"]: r["flow"] == "h" for r in FRAME}
    rw = S.risk_weighted(FRAME, 300, lambda r: r["risk"])
    assert abs(S.hajek(rw, fail) - 0.1) < 0.05


def test_manifest_detects_changed_frame():
    ids = [r["trace_id"] for r in FRAME]
    m = S.manifest("x", "uniform", {}, "q", ids, S.uniform(FRAME, 10), 2026, "0.5.0")
    assert S.verify(m, ids)
    with pytest.raises(ValueError):
        S.verify(m, ids[1:])


def test_fuzzy_link_and_maturity():
    tr = [{"trace_id": "a", "borrower_token": "B", "started_at_utc": "2026-10-01T10:00:00"},
          {"trace_id": "b", "borrower_token": "B", "started_at_utc": "2026-10-05T10:00:00"}]
    out = [{"outcome_id": "o1", "borrower_token": "B", "occurred_at_utc": "2026-10-06T09:00:00"},
           {"outcome_id": "o2", "borrower_token": "B", "occurred_at_utc": "2026-10-20T09:00:00"}]
    links = link_fuzzy(tr, out, 7)
    assert links == {"o1": "b"}
    assert score_links(links, {"o1": "a"}) == (0.0, 0.0)
    assert [t["trace_id"] for t in matured(tr, 20, "2026-10-22T00:00:00")] == ["a"]
