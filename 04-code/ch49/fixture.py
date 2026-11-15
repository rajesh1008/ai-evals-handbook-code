"""Ch49 teaching fixture: twelve-month SIMULATED Harbor scoreboard. Seed 2049."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).parent / "out"
SEED = 2049
# Ch16 kinds — never mutate / never treat as invoice
CH16 = {
    "usage_incurred_usd": 6.191862,
    "uncertain_reserve_usd": 0.050079,
    "policy_headroom_usd": 0.05,
    "ceiling_usd": 6.291941,
    "note": "kinds under $12 cap; not invoice; not historical cache recovery",
}


def build():
    rng = random.Random(SEED)
    months = []
    # SIMULATED illustrative Harbor Year-1 — not observed client history
    # wrong-offer Wilson hi (approx teaching), fee hi, kappa, annotator_new_share, incidents, ship
    base_wrong = [0.0143, 0.0128, 0.0111, 0.0098, 0.0091, 0.0086,
                  0.0084, 0.0081, 0.0079, 0.0088, 0.0119, 0.0082]
    base_fee = [0.028, 0.026, 0.024, 0.022, 0.021, 0.020,
                0.019, 0.0185, 0.018, 0.0195, 0.023, 0.0182]
    kappa = [0.61, 0.63, 0.64, 0.66, 0.67, 0.68,
             0.62, 0.64, 0.66, 0.65, 0.58, 0.63]  # M7 turnover dip; M11 dual-drift
    new_ann = [0.40, 0.35, 0.30, 0.25, 0.20, 0.18,
               0.45, 0.38, 0.30, 0.28, 0.25, 0.22]  # M7 hiring wave
    incidents = [2, 1, 1, 0, 1, 0, 3, 1, 1, 2, 4, 1]
    # M11: release passed gates then rolled back
    ship = ["HOLD", "SHIP", "SHIP", "SHIP", "SHIP", "SHIP",
            "SHIP", "SHIP", "SHIP", "SHIP", "ROLLBACK", "SHIP"]
    judge_pin = ["judge-v1"] * 4 + ["judge-v2"] * 3 + ["judge-v3"] * 3 + ["judge-v3-broken", "judge-v4"]
    sys_pin = ["sys-m1"] * 3 + ["sys-m2"] * 4 + ["sys-m3"] * 3 + ["sys-m3-depr", "sys-m4"]
    for m in range(1, 13):
        i = m - 1
        months.append({
            "month": m,
            "label": f"Y1-M{m:02d}",
            "wrong_offer_wilson_hi": base_wrong[i],
            "fee_wilson_hi": base_fee[i],
            "annotator_kappa": kappa[i],
            "new_annotator_share": new_ann[i],
            "incident_count": incidents[i],
            "ship_verb": ship[i],
            "system_pin": sys_pin[i],
            "judge_pin": judge_pin[i],
            "kind": "SIMULATED",
            "note": "illustrative Harbor Year-1 teaching freeze; not observed client history",
        })
    calendar = [
        {"month": m, "artifact": art, "owner": own, "trigger": trig}
        for m, art, own, trig in [
            (1, "Year plan + registry freeze", "EvalLead", "calendar_start"),
            (2, "First quarterly baseline draft", "EvalLead", "Q1_slot"),
            (3, "Q1 re-baseline signed", "Victor", "quarter_close"),
            (4, "Model upgrade ticket M2→M3", "Ryan", "provider_bump"),
            (5, "Judge revalidation slot", "Grace", "quarterly_judge"),
            (6, "Q2 re-baseline signed", "Victor", "quarter_close"),
            (7, "Annotator onboarding wave", "EvalLead", "turnover"),
            (8, "Policy v5 + judge rubric retune", "Victor+Grace", "policy_change"),
            (9, "Q3 re-baseline + mix-shock review", "EvalLead", "quarter_close"),
            (10, "Shadow hours before M3→M4", "Ryan", "provider_bump"),
            (11, "RC-49-11 ship then rollback", "EvalLead+Victor", "incident"),
            (12, "Q4 re-baseline + Year-1 packet", "Victor", "quarter_close"),
        ]
    ]
    events = {
        "annotator_turnover_m7": {"departed": "GraceHolloway_primary", "new": 2, "kappa_pre": 0.68, "kappa_post": 0.62},
        "policy_change_m8": {"from": "hardship-policy-v4", "to": "hardship-policy-v5", "judge_retune_required": True},
        "provider_deprecation_m11": {
            "system_pin_before": "sys-m3",
            "system_pin_after": "sys-m3-depr",
            "judge_pin_before": "judge-v3",
            "judge_pin_after": "judge-v3-broken",
            "both_changed": True,
            "caught_by": "pin_diff_gate",
        },
        "rollback_rc_49_11": {
            "candidate": "RC-49-11",
            "gates_green": True,
            "online_complaint_spike": True,
            "action": "ROLLBACK_WITHIN_72H",
            "lesson": "gate_green_not_trial_level_surrogacy",
        },
        "sidebar_q2_judge_skipped": {
            "quarter": "Q2",
            "judge_revalidation_scheduled": True,
            "executed": False,
            "consequence": "M8 policy change hit stale rubric",
        },
    }
    raw = json.dumps({"seed": SEED, "months": months, "calendar": calendar, "events": events, "CH16": CH16},
                     sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    fix = {
        "seed": SEED,
        "digest": digest,
        "SIMULATED": True,
        "live_provider_sweeps": "PENDING",
        "months": months,
        "calendar": calendar,
        "events": events,
        "CH16": CH16,
        "n_months": 12,
        "label": "Harbor Year-1 illustrative SIMULATED scoreboard",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fixture.json").write_text(json.dumps(fix, indent=2))
    return fix


if __name__ == "__main__":
    f = build()
    print(json.dumps({"digest": f["digest"], "seed": f["seed"], "n_months": f["n_months"]}, indent=2))
