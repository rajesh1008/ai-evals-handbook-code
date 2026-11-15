"""Deterministic Harbor acceptance cases for Ch44 vendor trial (offline)."""
from __future__ import annotations
from truss.vendorbox import AcceptanceCase

SEED = 2044
N = 120
VENDOR_CLAIM_RATE = 0.97  # vendor-published demo accuracy (teaching claim)


def build_cases(n: int = N, seed: int = SEED) -> list[AcceptanceCase]:
    cases = []
    # Mark every 5th case as also present in the vendor demo pack (overlap inject)
    for i in range(n):
        cid = f"h-v44-{seed}-{i:03d}"
        expected_defer = (i % 7 == 0)  # policy: prior deferral / income missing
        gold_wrong = expected_defer or (i % 11 == 0)
        cases.append(
            AcceptanceCase(
                case_id=cid,
                flow="hardship_adjacent",
                input_text=f"borrower hardship inquiry case {i}",
                expected_defer=expected_defer,
                gold_wrong_offer=gold_wrong,
                in_vendor_demo=(i % 5 == 0),
            )
        )
    return cases
