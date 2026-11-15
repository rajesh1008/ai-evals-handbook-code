from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.guardmon import evaluate_guard, vocabulary_overrefuse, hardship_guard_coverage

OUT = Path(__file__).parent / "out"


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    m = evaluate_guard([c["pred"] for c in fix["cases"]], [c["gold"] for c in fix["cases"]])
    v = vocabulary_overrefuse(fix["cases"][:50], scary_words=fix["scary_words"])
    c = hardship_guard_coverage(10, 10)
    out = {
        "try_evaluate_guard_n": m["n"],
        "try_vocab_keys": sorted(v.keys()),
        "try_coverage_100": c["meets_100pct"],
    }
    (OUT / "try_its.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
