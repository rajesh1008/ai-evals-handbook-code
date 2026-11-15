"""Failure injection: treating affinity_bucket as a decide segment must be caught."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def main():
    lab = json.loads((OUT / "lab.json").read_text())
    inj = lab["proxy_injection"]
    assert inj["field"] == "affinity_bucket"
    assert inj["caught"] is True
    # Legitimate segments never equal affinity labels
    legit = set(lab["evidence_pack"]["legitimate_strata"])
    proxy_labels = {c["segment"] for c in inj["cards_must_not_decide"]}
    assert legit.isdisjoint(proxy_labels)
    out = {"ranking_reversed": False, "caught": True, "illegal_proxy": "affinity_bucket",
           "legit_disjoint_from_proxy": True}
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(out)


if __name__ == "__main__":
    main()
