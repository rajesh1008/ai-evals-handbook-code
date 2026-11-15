"""Failure injection: unpaired comparison reverses ranking."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def main():
    lab = json.loads((OUT / "lab.json").read_text())
    assert lab["ranking_reversed"] is True
    out = {
        "injection": "unpaired_comparison_reverses_ranking",
        "paired_ranking": lab["paired"]["ranking"],
        "unpaired_ranking": lab["unpaired_injection"]["ranking"],
        "caught": True,
        "digest": lab["digest"],
    }
    (OUT / "inject.json").write_text(json.dumps(out, indent=2))
    print(out)


if __name__ == "__main__":
    main()
