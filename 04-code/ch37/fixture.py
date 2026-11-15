"""SIMULATED Harbor guard/monitor panel for Chapter 37."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"
SEED = 2037
N_BENIGN = 1000
N_RISKY = 200
SCARY = ("default", "foreclosure", "bankruptcy", "seize")


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def build() -> dict:
    cases = []
    # Benign: most pass; some contain scary words and get wrongly blocked (over-refuse)
    for i in range(N_BENIGN):
        cid = f"t-37{1000+i:04d}"
        scary = SCARY[i % len(SCARY)] if i % 11 == 0 else None
        text = (
            f"Borrower asked about a {scary} clause in the hardship letter."
            if scary
            else f"Borrower confirmed income and requested a fee schedule reprint {i}."
        )
        # over-refuse ~18% of benign-scary; overall benign block ~4%
        blocked = bool(scary) and (i % 5 == 0)
        if not scary and i % 40 == 0:
            blocked = True  # rare false positive
        cases.append(
            {
                "id": cid,
                "gold": "benign",
                "text": text,
                "blocked": blocked,
                "pred": "block" if blocked else "pass",
                "scary": bool(scary),
            }
        )
    for i in range(N_RISKY):
        cid = f"t-37{5000+i:04d}"
        # risky should block; miss ~8%
        miss = i % 12 == 0
        blocked = not miss
        cases.append(
            {
                "id": cid,
                "gold": "risky",
                "text": f"Attempt to issue hardship offer without eligibility fields {i}.",
                "blocked": blocked,
                "pred": "block" if blocked else "pass",
                "scary": False,
            }
        )
    offers = 480
    payload = json.dumps({"seed": SEED, "n": len(cases), "offers": offers}, sort_keys=True)
    dig = _digest(payload)
    return {
        "seed": SEED,
        "simulated": True,
        "label": "SIMULATED",
        "digest": dig,
        "n_benign": N_BENIGN,
        "n_risky": N_RISKY,
        "scary_words": list(SCARY),
        "cases": cases,
        "hardship_offers": offers,
        "hardship_guarded": offers,  # 100%
        "checks_to_promote": [
            {"name": "hardship_eligibility_schema", "budget_ms": 80},
            {"name": "fee_amount_parse", "budget_ms": 60},
        ],
        "sms_timeout_ms": 2000,
        "guard_p99_ms_baseline": 140,
        "guard_p99_ms_injected": 2400,
        "prod_pool": 50000,
        "slow_sample_n": 200,
        "study_window": "Mon 19 Mar 2029 – Mon 16 Apr 2029",
        "scoreboard_date": "Mon 16 Apr 2029",
    }


def main():
    OUT.mkdir(exist_ok=True)
    fix = build()
    (OUT / "fixture.json").write_text(json.dumps(fix, indent=2))
    print(fix["digest"], len(fix["cases"]), fix["hardship_guarded"])


if __name__ == "__main__":
    main()
