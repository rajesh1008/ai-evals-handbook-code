"""Ch52 lab: hardening checklist finds judge version pinned nowhere."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def check_item(cfg: dict, item: str) -> dict:
    judge = cfg.get("judge") or {}
    if item == "judge_id_present":
        ok = bool(judge.get("id"))
        return {"item": item, "ok": ok, "detail": judge.get("id")}
    if item == "judge_version_pin":
        ver = judge.get("version")
        ok = bool(ver) and str(ver).strip() not in ("", "None", "null", "unpinned")
        return {
            "item": item,
            "ok": ok,
            "detail": ver,
            "finding": None if ok else "JUDGE_VERSION_PINNED_NOWHERE",
        }
    if item == "gold_n_gt_0":
        n = int(judge.get("gold_n") or 0)
        return {"item": item, "ok": n > 0, "detail": n}
    if item == "suite_digest_pin":
        d = str(cfg.get("suite_digest") or "")
        return {"item": item, "ok": len(d) >= 8, "detail": d[:12]}
    if item == "population_named":
        p = str(cfg.get("population") or "").strip()
        return {"item": item, "ok": bool(p), "detail": p}
    if item == "cost_kinds_present":
        ck = cfg.get("cost_kinds") or {}
        need = {"known_incurred_usd", "uncertain_reserve_usd", "policy_headroom_usd", "ceiling_sum_usd"}
        ok = need.issubset(set(ck.keys()))
        return {"item": item, "ok": ok, "detail": sorted(ck.keys()) if isinstance(ck, dict) else None}
    if item == "runbook_owner":
        return {"item": item, "ok": bool(cfg.get("runbook_owner")), "detail": cfg.get("runbook_owner")}
    if item == "edge_backlog_ranked":
        return {"item": item, "ok": bool(cfg.get("edge_backlog_ranked")), "detail": cfg.get("edge_backlog_ranked")}
    if item == "validated_flag_honest":
        return {"item": item, "ok": "validated" in judge, "detail": judge.get("validated")}
    if item == "inject_label_if_failure":
        if cfg.get("FAILURE_INJECTION"):
            return {
                "item": item,
                "ok": bool(cfg.get("inject_label")),
                "detail": cfg.get("inject_label"),
            }
        return {"item": item, "ok": True, "detail": "no_inject"}
    return {"item": item, "ok": False, "detail": "unknown_item"}


def harden(cfg: dict, items: list[str]) -> dict:
    results = [check_item(cfg, it) for it in items]
    fails = [r for r in results if not r["ok"]]
    findings = [r.get("finding") for r in fails if r.get("finding")]
    return {
        "config": cfg.get("name"),
        "checklist_pass": len(fails) == 0,
        "n_fail": len(fails),
        "fails": fails,
        "findings": findings,
        "FAILURE_INJECTION_CAUGHT": bool(
            cfg.get("FAILURE_INJECTION") and "JUDGE_VERSION_PINNED_NOWHERE" in findings
        ),
        "SIMULATED": True,
    }


def scoreboard_verdict(board: dict) -> dict:
    statuses = {r["owner"] + ":" + r["target"][:32]: r["status"] for r in board["rows"]}
    open_n = sum(1 for r in board["rows"] if r["status"] == "OPEN")
    return {
        "open_targets": open_n,
        "statuses": statuses,
        "all_green": open_n == 0,
        "SIMULATED": True,
        "note": "final scoreboard teaching lock; OPEN is honest not failure of the chapter",
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    items = fix["hardening_checklist_items"]
    reports = [harden(cfg, items) for cfg in fix["configs"]]
    inject = next(r for r in reports if r.get("FAILURE_INJECTION_CAUGHT"))
    board = scoreboard_verdict(fix["scoreboard"])
    evidence = {
        "control_objective": "hardening checklist finds judge version pinned nowhere; final scoreboard vs Rachel/Victor/Sarah",
        "seed": fix["seed"],
        "digest": fix["digest"],
        "hardening_reports": reports,
        "inject_caught": inject["FAILURE_INJECTION_CAUGHT"],
        "inject_config": inject["config"],
        "inject_finding": "JUDGE_VERSION_PINNED_NOWHERE",
        "scoreboard": fix["scoreboard"],
        "scoreboard_verdict": board,
        "edge_backlog_n": len(fix["edge_backlog"]),
        "CH16": fix["CH16"],
        "SIMULATED": True,
        "live_provider_sweeps": "PENDING",
    }
    blob = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    record = hashlib.sha256(blob).hexdigest()
    out = {
        "digest": fix["digest"],
        "record": {"record_sha256": record, "record_sha12": record[:12]},
        "evidence_pack": evidence,
    }
    (OUT / "lab.json").write_text(json.dumps(out, indent=2) + "\n")
    print(
        "lab record",
        record[:12],
        "inject",
        inject["FAILURE_INJECTION_CAUGHT"],
        "open_targets",
        board["open_targets"],
    )


if __name__ == "__main__":
    main()
