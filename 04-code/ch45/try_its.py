"""Try-it: drop hottest segment from display without shrinking declared family."""
from __future__ import annotations
import json
from pathlib import Path
OUT = Path(__file__).parent / "out"

def main():
    lab = json.loads((OUT / "lab.json").read_text())
    segs = lab["evidence_pack"]["pre_segments"]
    declared = len(segs)
    # Trophy anti-pattern: hide OPEN segment
    visible = [s for s in segs if s["meets_upper_bound_target"]]
    (OUT / "try_its.json").write_text(json.dumps({
        "declared_segments": declared,
        "visible_if_trophy": len(visible),
        "hidden_OPEN": declared - len(visible),
        "refuse": "hiding OPEN segments is trophy reporting",
    }, indent=2))
    print("try_its ok")

if __name__ == "__main__":
    main()
