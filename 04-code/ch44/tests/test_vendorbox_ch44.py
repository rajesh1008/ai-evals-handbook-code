from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "truss"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixture import build_cases, SEED
from truss.vendorbox import trial_api_respond, score_acceptance, inject_demo_overlap, HARDSHIP_WRONG_OFFER_CEILING

def test_fixture_size_and_overlap():
    cases = build_cases()
    assert len(cases) == 120
    assert sum(1 for c in cases if c.in_vendor_demo) == 24  # every 5th
    assert SEED == 2044

def test_clean_path_refuses_hardship_ceiling():
    cases = build_cases()
    resp = {c.case_id: trial_api_respond(c, contaminated_demo=False) for c in cases}
    r = score_acceptance(cases, resp, vendor_claim_rate=0.97)
    assert HARDSHIP_WRONG_OFFER_CEILING == 0.005
    assert r.admit is False
    assert r.wrong_offers > 0

def test_inject_moves_rate_toward_claim():
    inj = inject_demo_overlap(build_cases())
    assert inj["simulated"] is True
    assert inj["rate_moved_toward_claim"] is True
    assert inj["decline_purchase"] is True
    assert inj["overlap_count"] == 24

def test_lab_digest_stable():
    import lab
    p = lab.main()
    assert len(p["digest"]) == 16
    assert p["decline_purchase"] is True
    assert p["live_vendor_http"].startswith("PENDING")

def test_missing_traces_fail_closed():
    from truss.vendorbox import BlackBoxResponse, AcceptanceCase, score_acceptance
    c = AcceptanceCase("x", "hardship_adjacent", "t", True, True, False)
    r = BlackBoxResponse("x", "ok", [], False, True, False, "offline_trial_fixture")
    rec = score_acceptance([c], {"x": r}, vendor_claim_rate=0.9)
    assert rec.wrong_offers >= 1
