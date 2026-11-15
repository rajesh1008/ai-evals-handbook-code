from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "truss"))
from truss.vendorbox import wilson_upper, HARDSHIP_WRONG_OFFER_CEILING
from fixture import build_cases
from truss.vendorbox import trial_api_respond, score_acceptance

def main():
    cases = build_cases()
    resp = {c.case_id: trial_api_respond(c) for c in cases}
    r = score_acceptance(cases, resp, vendor_claim_rate=0.97)
    out = {
        "try_its": [
            {"name": "wilson_helper", "ok": wilson_upper(0, 800) < 0.005},
            {"name": "ceiling_constant", "ok": HARDSHIP_WRONG_OFFER_CEILING == 0.005},
            {"name": "n_cases", "ok": r.n == 120},
            {"name": "decline_when_not_admit", "ok": (not r.admit) == True or r.admit is False or True},
        ]
    }
    out["try_its"][-1]["ok"] = (r.admit is False)  # expect refuse on this fixture
    out["all_ok"] = all(t["ok"] for t in out["try_its"])
    Path(__file__).resolve().parent.joinpath("out/try_its.json").write_text(json.dumps(out, indent=2))
    return out

if __name__ == "__main__":
    print(main())
