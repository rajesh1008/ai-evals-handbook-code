"""Ch49 lab: twelve-month ops + dual-pin deprecation injection. Offline SIM."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def scoreboard_summary(months: list[dict]) -> dict:
    return {
        "n_months": len(months),
        "wrong_offer_hi_by_month": [m["wrong_offer_wilson_hi"] for m in months],
        "fee_hi_by_month": [m["fee_wilson_hi"] for m in months],
        "kappa_by_month": [m["annotator_kappa"] for m in months],
        "rollback_months": [m["month"] for m in months if m["ship_verb"] == "ROLLBACK"],
        "kind": "SIMULATED",
    }


def pin_diff_gate(before_sys: str, after_sys: str, before_judge: str, after_judge: str) -> dict:
    """Failure injection detection: provider deprecation changing system AND judge."""
    sys_changed = before_sys != after_sys
    judge_changed = before_judge != after_judge
    dual = sys_changed and judge_changed
    return {
        "system_changed": sys_changed,
        "judge_changed": judge_changed,
        "dual_change": dual,
        "verdict": "HOLD_DUAL_PIN" if dual else ("HOLD_SINGLE_PIN" if (sys_changed or judge_changed) else "PINS_STABLE"),
        "SIMULATED": True,
    }


def upgrade_ticket(sys_from: str, sys_to: str, judge_pin: str, gold_freeze: str) -> dict:
    return {
        "system_from": sys_from,
        "system_to": sys_to,
        "judge_pin": judge_pin,
        "gold_freeze": gold_freeze,
        "shadow_hours_required": 72,
        "refuse_if_missing": ["gold_freeze", "judge_pin", "shadow_hours"],
        "SIMULATED": True,
    }


def rollback_packet(events: dict) -> dict:
    r = events["rollback_rc_49_11"]
    return {
        **r,
        "surrogacy_note": "gates_green_is_not_trial_level_surrogacy",
        "live_ab_audit": "PENDING",
        "SIMULATED": True,
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    sb = scoreboard_summary(fix["months"])
    dep = fix["events"]["provider_deprecation_m11"]
    pin = pin_diff_gate(
        dep["system_pin_before"], dep["system_pin_after"],
        dep["judge_pin_before"], dep["judge_pin_after"],
    )
    ticket = upgrade_ticket("sys-m2", "sys-m3", "judge-v2", "gold-freeze-m4")
    rb = rollback_packet(fix["events"])
    evidence = {
        "control_objective": "operate eval practice across twelve months with owned calendar, dual-pin detection, and honest rollback",
        "digest": fix["digest"],
        "seed": fix["seed"],
        "scoreboard": sb,
        "calendar_rows": len(fix["calendar"]),
        "pin_diff": pin,
        "upgrade_ticket_example": ticket,
        "rollback": rb,
        "sidebar_q2_judge_skipped": fix["events"]["sidebar_q2_judge_skipped"],
        "annotator_turnover_m7": fix["events"]["annotator_turnover_m7"],
        "policy_change_m8": fix["events"]["policy_change_m8"],
        "CH16": fix["CH16"],
        "SIMULATED": True,
        "live_provider_sweeps": "PENDING",
        "label": fix["label"],
    }
    raw = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    record = {"record_sha12": hashlib.sha256(raw).hexdigest()[:12], "experiment_id": "ch49-twelve-month-ops"}
    payload = {"SIMULATED": True, "evidence_pack": evidence, "record": record, "digest": fix["digest"]}
    (OUT / "lab.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({
        "digest": fix["digest"],
        "record": record["record_sha12"],
        "rollback_months": sb["rollback_months"],
        "pin_verdict": pin["verdict"],
        "dual_change": pin["dual_change"],
    }, indent=2))


if __name__ == "__main__":
    main()
