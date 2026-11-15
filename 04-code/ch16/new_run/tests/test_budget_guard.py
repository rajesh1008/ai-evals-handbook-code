"""Mock tests for the hard $12 budget guard — NO paid API calls."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]  # 04-code/ch16
sys.path.insert(0, str(ROOT))

import budget as B


class BudgetGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger_path = Path(self.tmp.name) / "ledger.json"
        os.environ["CH16_BUDGET_CAP"] = "12"
        os.environ["CH16_BUDGET_HEADROOM"] = "0.05"
        os.environ["CH16_BUDGET_LEDGER"] = str(self.ledger_path)
        os.environ["CH16_RUN_ID"] = "test-run"
        B.reset_ledger_singleton_for_tests()

    def tearDown(self):
        B.reset_ledger_singleton_for_tests()
        self.tmp.cleanup()
        for k in ("CH16_BUDGET_CAP", "CH16_BUDGET_HEADROOM", "CH16_BUDGET_LEDGER", "CH16_RUN_ID"):
            os.environ.pop(k, None)

    def test_overcap_refused(self):
        led = B.get_ledger()
        # Reserve almost all: 12 - 0.05 headroom = 11.95
        led.reserve(11.90, meta={"t": "big"})
        with self.assertRaises(B.BudgetExhausted):
            led.reserve(0.10, meta={"t": "overflow"})

    def test_parallel_reservation_race(self):
        led = B.get_ledger()
        # Each reservation 1.00; headroom 0.05 → at most 11 successes
        ok = []
        err = []
        lock = threading.Lock()

        def worker(_):
            try:
                rid = led.reserve(1.00, meta={"w": _})
                with lock:
                    ok.append(rid)
            except B.BudgetExhausted:
                with lock:
                    err.append(1)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(ok), 11)  # 11*1.00 + 0.05 = 11.05 <= 12; 12th would need 12.05
        self.assertEqual(len(err), 9)
        snap = led.remaining_cap()
        self.assertAlmostEqual(snap["outstanding_reserved_usd"], 11.0, places=5)
        self.assertGreaterEqual(snap["available_usd"], 0.0)

    def test_commit_reduces_outstanding_and_charges(self):
        led = B.get_ledger()
        rid = led.reserve(0.50)
        led.commit(rid, 0.12)
        snap = led.remaining_cap()
        self.assertAlmostEqual(snap["charged_usd"], 0.12, places=5)
        self.assertEqual(snap["open_reservations"], 0)
        self.assertEqual(snap["committed"], 1)

    def test_error_unreconciled_holds_reservation(self):
        led = B.get_ledger()
        rid = led.reserve(0.40)
        led.mark_unreconciled(rid, "APIStatusError: 500")
        snap = led.remaining_cap()
        self.assertEqual(snap["unreconciled"], 1)
        self.assertAlmostEqual(snap["outstanding_reserved_usd"], 0.40, places=5)
        # Cannot use that money for a new call
        with self.assertRaises(B.BudgetExhausted):
            # fill rest then fail
            led.reserve(11.56)  # 0.40 + 11.56 + 0.05 = 12.01 > 12

    def test_release_frees_budget(self):
        led = B.get_ledger()
        rid = led.reserve(5.0)
        led.release(rid, "connection_error")
        rid2 = led.reserve(5.0)  # should succeed
        self.assertTrue(rid2)

    def test_resume_same_ledger(self):
        led = B.get_ledger()
        rid = led.reserve(2.0)
        led.commit(rid, 1.5)
        B.reset_ledger_singleton_for_tests()
        led2 = B.get_ledger()
        snap = led2.remaining_cap()
        self.assertAlmostEqual(snap["charged_usd"], 1.5, places=5)
        self.assertEqual(snap["committed"], 1)

    def test_unpriced_model_refused(self):
        with self.assertRaises(B.BudgetError):
            B.assert_model_priced("gpt-4o")

    def test_worst_case_uses_max_tokens_and_price(self):
        req = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": "hi" * 100}],
        }
        w = B.worst_case_usd(req)
        # Must be at least max_tokens * $5 / 1e6
        self.assertGreaterEqual(w, 1000 * 5 / 1e6)

    def test_cache_hit_path_no_budget(self):
        """llm.run with live=False and empty cache returns {} without ledger writes."""
        import llm
        os.environ["CH16_OUT"] = self.tmp.name
        # reload OUT
        llm.OUT = Path(self.tmp.name)
        before = B.get_ledger().remaining_cap()
        out = llm.run("cachetest", [("a", {"model": B.PRICE and "claude-haiku-4-5-20251001",
                                           "max_tokens": 10,
                                           "messages": [{"role": "user", "content": "x"}]})], live=False)
        after = B.get_ledger().remaining_cap()
        self.assertEqual(out, {})
        self.assertEqual(before["charged_usd"], after["charged_usd"])
        self.assertEqual(before["open_reservations"], after["open_reservations"])

    def test_llm_call_reserves_and_commits(self):
        import llm
        llm.OUT = Path(self.tmp.name)

        class FakeUsage:
            input_tokens = 100
            output_tokens = 50

        class FakeBlock:
            type = "text"
            text = "hello"

        class FakeMsg:
            content = [FakeBlock()]
            model = "claude-haiku-4-5-20251001"
            usage = FakeUsage()
            stop_reason = "end_turn"
            id = "msg_test"

        class FakeMessages:
            def create(self, **kwargs):
                return FakeMsg()

        class FakeClient:
            def __init__(self, *a, **k):
                self.messages = FakeMessages()

        req = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "hello world"}],
        }
        with mock.patch("anthropic.Anthropic", FakeClient):
            rec = llm._call(req, tag="t", item="i1")
        self.assertEqual(rec["text"], "hello")
        snap = B.get_ledger().remaining_cap()
        self.assertEqual(snap["committed"], 1)
        self.assertEqual(snap["open_reservations"], 0)
        # actual = (100*1 + 50*5)/1e6 = 0.00035
        self.assertAlmostEqual(snap["charged_usd"], 0.00035, places=6)

    def test_llm_call_overcap_before_dispatch(self):
        import llm
        llm.OUT = Path(self.tmp.name)
        led = B.get_ledger()
        led.reserve(11.94)  # almost full with headroom 0.05
        created = []

        class FakeMessages:
            def create(self, **kwargs):
                created.append(1)
                raise AssertionError("must not dispatch")

        class FakeClient:
            def __init__(self, *a, **k):
                self.messages = FakeMessages()

        req = {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 1200,
            "messages": [{"role": "user", "content": "x" * 5000}],
        }
        with mock.patch("anthropic.Anthropic", FakeClient):
            with self.assertRaises(B.BudgetExhausted):
                llm._call(req, tag="t", item="i2")
        self.assertEqual(created, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
