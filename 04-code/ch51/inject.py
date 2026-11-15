"""Failure injection: a taxonomy that does not translate (Hartford clinical → Toronto telecom)."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def translate_taxonomy(src_labels: list[str], dst_domain: str) -> dict:
    """Applying clinical prior-auth labels to telecom billing traces."""
    allowed_telecom = {"wrong_balance", "plan_mismatch", "handoff_late", "tone_fail", "BillingCycleEdge"}
    foreign = [x for x in src_labels if x not in allowed_telecom]
    return {
        "src_domain": "prior_authorization",
        "dst_domain": dst_domain,
        "src_labels": src_labels,
        "foreign_labels": foreign,
        "coverage": round((len(src_labels) - len(foreign)) / max(len(src_labels), 1), 4),
        "verdict": "HOLD_TAXONOMY_NONTRANSLATE" if foreign else "TAXONOMY_OK",
        "SIMULATED": True,
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    hartford = fix["cases"]["hartford"]["taxonomy"]
    inj = translate_taxonomy(hartford, "telecom_billing_support")
    # control: native telecom taxonomy should pass
    native = translate_taxonomy(
        fix["cases"]["toronto"]["taxonomy_offline"] + ["BillingCycleEdge"],
        "telecom_billing_support",
    )
    # native labels are all in allowed set after adding BillingCycleEdge — but wrong_balance etc. are allowed
    out = {"foreign": inj, "native_control": native, "SIMULATED": True}
    (OUT / "inject.json").write_text(json.dumps(out, indent=2) + "\n")
    print("inject", inj["verdict"], "foreign", inj["foreign_labels"], "native", native["verdict"])


if __name__ == "__main__":
    main()
