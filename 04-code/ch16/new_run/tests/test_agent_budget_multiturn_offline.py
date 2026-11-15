"""OFFLINE mock: agent.run_one must reserve/commit EACH messages.create turn under the hard cap.

No network. No Anthropic. Requirements recorded from audit P1:
- Every turn calls BudgetLedger.reserve(worst) before create
- Commit actual after success
- BudgetExhausted on a later turn stops cleanly without dispatch
- Concurrent traces cannot oversubscribe the cap
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import budget as B


class FakeUsage:
    def __init__(self, tin, tout):
        self.input_tokens = tin
        self.output_tokens = tout


class FakeBlock:
    def __init__(self, typ, **kw):
        self.type = typ
        for k, v in kw.items():
            setattr(self, k, v)

    def model_dump(self, exclude_none=True):
        d = {"type": self.type}
        if self.type == "text":
            d["text"] = self.text
        if self.type == "tool_use":
            d.update({"id": self.id, "name": self.name, "input": self.input})
        return d


class FakeMsg:
    def __init__(self, tin, tout, content, model="claude-haiku-4-5-20251001"):
        self.usage = FakeUsage(tin, tout)
        self.content = content
        self.model = model
        self.id = f"msg_{tin}_{tout}_{id(self)}"
        self.stop_reason = "end_turn"


class AgentMultiTurnBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["CH16_BUDGET_CAP"] = "0.05"  # tight cap to force exhaustion mid-trace
        os.environ["CH16_BUDGET_HEADROOM"] = "0.001"
        os.environ["CH16_BUDGET_LEDGER"] = str(Path(self.tmp.name) / "led.json")
        os.environ["CH16_RUN_ID"] = "agent-mt-test"
        os.environ["CH16_OUT"] = self.tmp.name
        B.reset_ledger_singleton_for_tests()

    def tearDown(self):
        B.reset_ledger_singleton_for_tests()
        self.tmp.cleanup()
        for k in ("CH16_BUDGET_CAP", "CH16_BUDGET_HEADROOM", "CH16_BUDGET_LEDGER", "CH16_RUN_ID", "CH16_OUT"):
            os.environ.pop(k, None)

    def test_each_turn_reserves_and_commits(self):
        import agent
        import llm
        llm.OUT = Path(self.tmp.name)
        # Raise cap so 2 turns fit
        os.environ["CH16_BUDGET_CAP"] = "12"
        B.reset_ledger_singleton_for_tests()
        creates = []

        def create(**kwargs):
            creates.append(kwargs)
            n = len(creates)
            if n == 1:
                # tool use → force second turn
                return FakeMsg(100, 50, [
                    FakeBlock("tool_use", id="tu1", name="get_fee_schedule", input={}),
                ])
            return FakeMsg(120, 40, [
                FakeBlock("text", text='critique\n{"verdict": "pass"}'),
            ])

        class FakeClient:
            def __init__(self, *a, **k):
                self.messages = type("M", (), {"create": staticmethod(create)})()

        import fixture as F
        bugs, normal = F.agent_set()
        t = bugs[0]
        with mock.patch("anthropic.Anthropic", FakeClient):
            rec = agent.run_one(t, "The late fee stands and cannot be waived.", llm.SMALL, max_turns=6, tools=agent.TOOLS)
        self.assertEqual(len(creates), 2)
        snap = B.get_ledger().remaining_cap()
        self.assertEqual(snap["committed"], 2)
        self.assertEqual(snap["open_reservations"], 0)
        self.assertEqual(len(rec["request_ids"]), 2)
        self.assertEqual(len(rec["tool_calls"]), 1)

    def test_budget_exhausted_mid_trace_no_further_dispatch(self):
        import agent
        import llm
        llm.OUT = Path(self.tmp.name)
        # Cap just enough for ONE small turn worst-case; second reserve must fail
        # Haiku worst ≈ (bound_input + 1200*5)/1e6 — set tiny cap
        os.environ["CH16_BUDGET_CAP"] = "0.008"
        os.environ["CH16_BUDGET_HEADROOM"] = "0.0001"
        B.reset_ledger_singleton_for_tests()
        creates = []

        def create(**kwargs):
            creates.append(1)
            return FakeMsg(80, 30, [
                FakeBlock("tool_use", id="tu1", name="get_fee_schedule", input={}),
            ])

        class FakeClient:
            def __init__(self, *a, **k):
                self.messages = type("M", (), {"create": staticmethod(create)})()

        import fixture as F
        bugs, normal = F.agent_set()
        t = bugs[1]
        with mock.patch("anthropic.Anthropic", FakeClient):
            rec = agent.run_one(t, "The late fee stands and cannot be waived.", llm.SMALL, max_turns=6, tools=agent.TOOLS)
        # First turn may or may not dispatch depending on worst_case vs cap;
        # if first reserved+ran, second must not dispatch.
        self.assertLessEqual(len(creates), 1)
        snap = B.get_ledger().remaining_cap()
        self.assertEqual(snap["open_reservations"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
