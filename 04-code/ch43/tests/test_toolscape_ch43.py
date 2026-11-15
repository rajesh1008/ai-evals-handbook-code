from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "truss"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from truss.toolscape import run_all_platforms, inject_judge_version_drift, HARDSHIP_WRONG_OFFER_CEILING
from fixture import build_cases

def test_six_platforms_admit_on_clean_fixture():
    rec = run_all_platforms(build_cases(), "harbor-hardship-judge@2026-11-01")
    assert len(rec) == 6
    assert all(r.admit for r in rec.values())
    assert HARDSHIP_WRONG_OFFER_CEILING == 0.005

def test_inject_changes_gate():
    inj = inject_judge_version_drift(
        build_cases(),
        pinned_version="harbor-hardship-judge@2026-11-01",
        default_version="platform-default-judge@unpinned",
        platform="langsmith",
    )
    assert inj["detect"]
    assert inj["gate_changed"]
    assert inj["pinned"]["admit"] is True
    assert inj["drifted"]["admit"] is False

def test_lab_output_digest_stable():
    import lab
    p = lab.main()
    assert p["all_pinned_admit"] is True
    assert len(p["digest"]) == 16

def test_format_envelopes_validate_and_same_gate():
    from truss.toolscape import PLATFORMS, adapt_with_envelope, build_format_envelope, validate_format_envelope
    cases = build_cases()
    judge = "harbor-hardship-judge@2026-11-01"
    receipts = []
    for p in PLATFORMS:
        env = build_format_envelope(p, cases, judge)
        assert validate_format_envelope(p, env) == []
        assert env["kind"] == "offline_format_envelope"
        out = adapt_with_envelope(p, cases, judge)
        receipts.append(out["receipt"])
        assert out["receipt"].platform == p
        assert out["receipt"].admit is True
    # all identical math aside from platform string
    assert len({(r.n, r.wrong_offers, r.wilson_upper, r.admit, r.judge_version) for r in receipts}) == 1

def test_envelope_missing_key_detected():
    from truss.toolscape import validate_format_envelope
    assert "judge_version" in validate_format_envelope("langfuse", {"dataset_name": "x", "items": [], "experiment_name": "e", "scores": []})

def test_adapters_are_normalised_contract_fixtures():
    """Documented honesty: adapt_* differ only by platform string on shared gate math."""
    from truss.toolscape import adapt_langfuse, adapt_phoenix, adapt_promptfoo
    cases = build_cases()
    a = adapt_langfuse(cases, "j@1")
    b = adapt_phoenix(cases, "j@1")
    c = adapt_promptfoo(cases, "j@1")
    assert a.n == b.n == c.n
    assert a.wrong_offers == b.wrong_offers == c.wrong_offers
    assert a.wilson_upper == b.wilson_upper == c.wilson_upper
    assert a.admit == b.admit == c.admit
    assert a.platform != b.platform != c.platform
