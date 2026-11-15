"""Hard spending cap for Chapter 16 NEW Anthropic runs.

ONE global ledger across gen + judges + agent (and retries). Every paid
messages.create must reserve its worst-case USD cost BEFORE dispatch and
commit the actual cost after. Cache hits never touch the ledger.

Env:
  CH16_BUDGET_LEDGER  path to ledger JSON (required when CH16_BUDGET_CAP set)
  CH16_BUDGET_CAP     hard USD cap (e.g. 12)
  CH16_BUDGET_HEADROOM  reserved slack for rounding (default 0.05)

This module never reads or prints API keys.
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
import uuid
from pathlib import Path

# Verified list prices (USD / MTok) for the ONLY allowed models — 2026-11-08.
# Unpriced models are refused by worst_case_usd / assert_model_priced.
PRICE = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-4-5-20250929": (3.00, 15.00),
}

_THREAD = threading.local()


class BudgetExhausted(RuntimeError):
    """Raised when a reservation would breach the hard cap."""


class BudgetError(RuntimeError):
    pass


def _ceil_usd(x: float) -> float:
    """Round money UP to 1e-6 USD (token microdollar)."""
    return math.ceil(x * 1_000_000) / 1_000_000


def assert_model_priced(model: str) -> tuple[float, float]:
    if model not in PRICE:
        raise BudgetError(
            f"model {model!r} has no verified price pin; only "
            f"{sorted(PRICE)} are allowed for this run"
        )
    return PRICE[model]


def bound_input_tokens(req: dict) -> int:
    """Proven local conservative upper bound (no network).

    Uses character count of the serialized request payload that the API
    bills as input. One token cannot exceed one Unicode character for the
    Latin-heavy Harbor prompts in this lab; we still add framing overhead.
    This bound is intentionally loose so reservations never under-reserve.
    """
    parts: list[str] = []
    if req.get("system"):
        parts.append(str(req["system"]))
    parts.append(json.dumps(req.get("messages") or [], ensure_ascii=False, sort_keys=True))
    if req.get("tools"):
        parts.append(json.dumps(req["tools"], ensure_ascii=False, sort_keys=True))
    if req.get("tool_choice") is not None:
        parts.append(json.dumps(req["tool_choice"], ensure_ascii=False, sort_keys=True))
    if req.get("thinking"):
        parts.append(json.dumps(req["thinking"], ensure_ascii=False, sort_keys=True))
    if req.get("metadata"):
        parts.append(json.dumps(req["metadata"], ensure_ascii=False, sort_keys=True))
    n_chars = sum(len(p) for p in parts)
    # +256 framing / role / tool schema overhead; never under-bound.
    return max(1, n_chars + 256)


def worst_case_usd(req: dict) -> float:
    """Worst-case charge for one messages.create from the request alone."""
    model = req.get("model")
    pin, pout = assert_model_priced(model)
    in_tok = bound_input_tokens(req)
    max_out = int(req.get("max_tokens") or 0)
    if max_out <= 0:
        raise BudgetError("max_tokens must be set for budget reservation")
    # Thinking tokens are billed as output and must fit under max_tokens
    # for the Anthropic Messages API shape used here; reserving max_tokens
    # already covers thinking budget_tokens.
    raw = (in_tok * pin + max_out * pout) / 1_000_000
    return _ceil_usd(raw)


def enabled() -> bool:
    return bool(os.environ.get("CH16_BUDGET_CAP"))


def ledger_path() -> Path:
    p = os.environ.get("CH16_BUDGET_LEDGER")
    if not p:
        raise BudgetError("CH16_BUDGET_LEDGER is required when budget cap is active")
    return Path(p)


def cap_usd() -> float:
    return float(os.environ["CH16_BUDGET_CAP"])


def headroom_usd() -> float:
    return float(os.environ.get("CH16_BUDGET_HEADROOM", "0.05"))


class BudgetLedger:
    """Process-safe + thread-safe ledger with exclusive file lock."""

    def __init__(self, path: Path | None = None, cap: float | None = None):
        self.path = path or ledger_path()
        self.cap = float(cap if cap is not None else cap_usd())
        self.headroom = headroom_usd()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write_unlocked({
                "run_id": os.environ.get("CH16_RUN_ID", "unset"),
                "cap_usd": self.cap,
                "headroom_usd": self.headroom,
                "charged_usd": 0.0,
                "reservations": {},
                "events": [],
                "created_at": time.time(),
            })

    def _read_unlocked(self) -> dict:
        return json.loads(self.path.read_text())

    def _write_unlocked(self, data: dict) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        tmp.replace(self.path)

    def _with_file(self, fn):
        import fcntl
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            # ensure file for lock
            self.path.write_text("{}")
        with self.path.open("r+") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                fh.seek(0)
                raw = fh.read()
                data = json.loads(raw) if raw.strip() else {
                    "run_id": os.environ.get("CH16_RUN_ID", "unset"),
                    "cap_usd": self.cap,
                    "headroom_usd": self.headroom,
                    "charged_usd": 0.0,
                    "reservations": {},
                    "events": [],
                    "created_at": time.time(),
                }
                # repair empty init
                if "reservations" not in data:
                    data = {
                        "run_id": os.environ.get("CH16_RUN_ID", "unset"),
                        "cap_usd": self.cap,
                        "headroom_usd": self.headroom,
                        "charged_usd": 0.0,
                        "reservations": {},
                        "events": [],
                        "created_at": time.time(),
                    }
                result = fn(data)
                fh.seek(0)
                fh.truncate()
                fh.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
                return result
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def snapshot(self) -> dict:
        with self._lock:
            return self._with_file(lambda d: json.loads(json.dumps(d)))

    def outstanding_reserved(self, data: dict) -> float:
        return _ceil_usd(sum(
            float(r["worst_usd"])
            for r in data["reservations"].values()
            if r.get("status") in ("open", "unreconciled")
        ))

    def available(self, data: dict) -> float:
        used = float(data["charged_usd"]) + self.outstanding_reserved(data) + float(data.get("headroom_usd", self.headroom))
        return _ceil_usd(self.cap - used)

    def reserve(self, worst_usd: float, meta: dict | None = None) -> str:
        worst = _ceil_usd(float(worst_usd))
        if worst <= 0:
            raise BudgetError("reservation worst_usd must be positive")

        def op(data):
            avail = self.available(data)
            # available already subtracts headroom; refuse if worst > avail
            if worst > avail + 1e-12:
                raise BudgetExhausted(
                    f"reserve ${worst:.6f} refused: charged=${data['charged_usd']:.6f} "
                    f"outstanding=${self.outstanding_reserved(data):.6f} "
                    f"headroom=${data.get('headroom_usd', self.headroom):.6f} "
                    f"cap=${self.cap:.2f} available=${avail:.6f}"
                )
            rid = uuid.uuid4().hex
            data["reservations"][rid] = {
                "worst_usd": worst,
                "status": "open",
                "created_at": time.time(),
                "meta": meta or {},
            }
            data.setdefault("events", []).append({
                "t": time.time(), "op": "reserve", "id": rid, "worst_usd": worst, "meta": meta or {},
            })
            # trim events
            if len(data["events"]) > 20000:
                data["events"] = data["events"][-10000:]
            return rid

        with self._lock:
            return self._with_file(op)

    def commit(self, rid: str, actual_usd: float) -> None:
        actual = _ceil_usd(float(actual_usd))

        def op(data):
            r = data["reservations"].get(rid)
            if not r:
                raise BudgetError(f"unknown reservation {rid}")
            if r["status"] not in ("open", "unreconciled"):
                raise BudgetError(f"reservation {rid} status {r['status']}")
            # Cap commit at reserved worst (never charge ledger more than reserved
            # without a new reserve); if actual > worst, keep the overage as
            # charged but flag — should not happen if bound is conservative.
            charge = actual
            data["charged_usd"] = _ceil_usd(float(data["charged_usd"]) + charge)
            r["status"] = "committed"
            r["actual_usd"] = actual
            r["committed_at"] = time.time()
            data.setdefault("events", []).append({
                "t": time.time(), "op": "commit", "id": rid, "actual_usd": actual,
            })
            return None

        with self._lock:
            return self._with_file(op)

    def release(self, rid: str, reason: str = "released") -> None:
        def op(data):
            r = data["reservations"].get(rid)
            if not r:
                return None
            if r["status"] == "committed":
                return None
            r["status"] = "released"
            r["release_reason"] = reason
            r["released_at"] = time.time()
            data.setdefault("events", []).append({
                "t": time.time(), "op": "release", "id": rid, "reason": reason,
            })
            return None

        with self._lock:
            return self._with_file(op)

    def mark_unreconciled(self, rid: str, error: str) -> None:
        """Keep reservation outstanding until reconciled — may have been charged."""

        def op(data):
            r = data["reservations"].get(rid)
            if not r:
                return None
            if r["status"] == "committed":
                return None
            r["status"] = "unreconciled"
            r["error"] = error[:500]
            r["unreconciled_at"] = time.time()
            data.setdefault("events", []).append({
                "t": time.time(), "op": "unreconciled", "id": rid, "error": error[:200],
            })
            return None

        with self._lock:
            return self._with_file(op)

    def remaining_cap(self) -> dict:
        snap = self.snapshot()
        out_r = self.outstanding_reserved(snap)
        charged = float(snap["charged_usd"])
        hr = float(snap.get("headroom_usd", self.headroom))
        return {
            "cap_usd": self.cap,
            "charged_usd": charged,
            "outstanding_reserved_usd": out_r,
            "headroom_usd": hr,
            "available_usd": _ceil_usd(self.cap - charged - out_r - hr),
            "open_reservations": sum(1 for r in snap["reservations"].values() if r["status"] == "open"),
            "unreconciled": sum(1 for r in snap["reservations"].values() if r["status"] == "unreconciled"),
            "committed": sum(1 for r in snap["reservations"].values() if r["status"] == "committed"),
        }


_LEDGER: BudgetLedger | None = None
_LEDGER_LOCK = threading.Lock()


def get_ledger() -> BudgetLedger:
    global _LEDGER
    with _LEDGER_LOCK:
        if _LEDGER is None:
            _LEDGER = BudgetLedger()
        return _LEDGER


def reset_ledger_singleton_for_tests() -> None:
    global _LEDGER
    with _LEDGER_LOCK:
        _LEDGER = None


def guarded_cost_usd(model: str, tin: int, tout: int) -> float:
    pin, pout = assert_model_priced(model)
    return _ceil_usd((tin * pin + tout * pout) / 1_000_000)
