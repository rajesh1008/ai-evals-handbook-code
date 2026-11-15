#!/usr/bin/env python3
"""Execute full NEW Ch16 lab under hard $12 budget. Writes only under this run dir via CH16_OUT."""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
CH16 = RUN_DIR.parents[1]  # 04-code/ch16
sys.path.insert(0, str(CH16))

# Env must be set before importing llm (OUT is read at import)
assert os.environ.get("CH16_BUDGET_CAP"), "CH16_BUDGET_CAP required"
assert os.environ.get("CH16_BUDGET_LEDGER"), "CH16_BUDGET_LEDGER required"
assert os.environ.get("CH16_OUT"), "CH16_OUT required"
assert os.environ.get("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY must be present (value never printed)"

import budget as B
import gen
import judges
import agent
import llm

LOG = RUN_DIR / "logs" / "run.log"
STATUS = RUN_DIR / "reports" / "status.json"


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(line + "\n")


def write_status(**kw):
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    cur = {}
    if STATUS.exists():
        cur = json.loads(STATUS.read_text())
    cur.update(kw)
    cur["budget"] = B.get_ledger().remaining_cap()
    cur["updated_at"] = time.time()
    STATUS.write_text(json.dumps(cur, indent=2) + "\n")


def count_jsonl(tag: str) -> int:
    p = Path(os.environ["CH16_OUT"]) / f"{tag}.jsonl"
    if not p.exists():
        return 0
    return sum(1 for ln in p.read_text().splitlines() if ln.strip())


def main():
    log(f"START run_id={os.environ.get('CH16_RUN_ID')} out={os.environ['CH16_OUT']} cap=${os.environ['CH16_BUDGET_CAP']}")
    write_status(phase="start", stages={})
    B.reset_ledger_singleton_for_tests()  # pick up env ledger path
    # ensure ledger exists
    B.get_ledger()

    stages = {}

    # --- GEN ---
    try:
        log("PHASE gen")
        write_status(phase="gen")
        t0 = time.time()
        R = gen.replies(live=True)
        A = gen.alt_replies(live=True)
        S = gen.spanish(live=True)
        u = llm.usage(list(R.values()) + list(A.values()) + list(S.values()))
        stages["gen"] = {
            "replies": len(R), "alt": len(A), "spanish": len(S),
            "usage": u, "sec": round(time.time() - t0, 1),
            "jsonl": {k: count_jsonl(k) for k in ("replies", "alt_replies", "spanish")},
        }
        log(f"GEN done replies={len(R)} alt={len(A)} spanish={len(S)} cost~${u['cost']:.4f}")
        write_status(phase="gen_done", stages=stages)
    except B.BudgetExhausted as e:
        log(f"GEN BUDGET STOP: {e}")
        stages["gen"] = {"stopped": "budget", "error": str(e)}
        write_status(phase="stopped_budget", stages=stages)
        return 2
    except Exception:
        log("GEN ERROR\n" + traceback.format_exc())
        write_status(phase="gen_error", stages=stages, error=traceback.format_exc())
        return 1

    # --- JUDGES ---
    try:
        log("PHASE judges")
        write_status(phase="judges", stages=stages)
        t0 = time.time()
        res = judges.load_all(live=True)
        detail = {}
        all_recs = []
        for k, v in res.items():
            u = llm.usage(v.values())
            detail[k] = {"n": len(v), "usage": u}
            all_recs.extend(v.values())
        u = llm.usage(all_recs)
        stages["judges"] = {
            "experiments": detail, "usage": u, "sec": round(time.time() - t0, 1),
            "jsonl_rows": count_jsonl("judge"),
        }
        log(f"JUDGES done rows={count_jsonl('judge')} cost~${u['cost']:.4f}")
        write_status(phase="judges_done", stages=stages)
    except B.BudgetExhausted as e:
        log(f"JUDGES BUDGET STOP: {e}")
        stages["judges"] = {"stopped": "budget", "error": str(e), "jsonl_rows": count_jsonl("judge")}
        write_status(phase="stopped_budget", stages=stages)
        return 2
    except Exception:
        log("JUDGES ERROR\n" + traceback.format_exc())
        write_status(phase="judges_error", stages=stages, error=traceback.format_exc())
        return 1

    # --- AGENT ---
    try:
        log("PHASE agent")
        write_status(phase="agent", stages=stages)
        t0 = time.time()
        agent_out = {}
        for m, calc in ((llm.SMALL, False), (llm.LARGE, False), (llm.SMALL, True)):
            d = agent.run(m, live=True, calc=calc)
            tag = "agent_" + ("large" if m == llm.LARGE else "small") + ("_calc" if calc else "")
            u = llm.usage(d.values())
            agent_out[tag] = {"n": len(d), "usage": u, "tools": sum(len(r.get("tool_calls") or []) for r in d.values())}
            log(f"  {tag}: n={len(d)} cost~${u['cost']:.4f}")
        stages["agent"] = {"variants": agent_out, "sec": round(time.time() - t0, 1)}
        write_status(phase="agent_done", stages=stages)
    except B.BudgetExhausted as e:
        log(f"AGENT BUDGET STOP: {e}")
        stages["agent"] = {"stopped": "budget", "error": str(e)}
        write_status(phase="stopped_budget", stages=stages)
        return 2
    except Exception:
        log("AGENT ERROR\n" + traceback.format_exc())
        write_status(phase="agent_error", stages=stages, error=traceback.format_exc())
        return 1

    rem = B.get_ledger().remaining_cap()
    log(f"COMPLETE charged=${rem['charged_usd']:.4f} available=${rem['available_usd']:.4f}")
    write_status(phase="complete", stages=stages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
