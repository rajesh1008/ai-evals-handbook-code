"""Pending live run: hardship-judge-v1, stated-change-judge-v1 and permission-judge-v1 on the
300 trial traces (100 development, 200 held-out).

No model is called by default. The chapter's numbers come from SIMULATED stand-ins (fixture.py).
With a provider client wired and `--live` passed, this script renders each judge's prompt with
truss.judge.render, sends it at temperature 0, parses the verdict with truss.judge.parse (never
coerced), and writes out/real_judge.json; lab.py and inject.py can then be pointed at those verdicts
in place of the planted ones. The output replaces every [RESULT PENDING] marker in Chapter 21.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "truss"))
import fixture as fx

dev, test = fx.build()
print("=" * 100)
print("Pending live run: the hardship judges on the trial set")
print("=" * 100)
print("  command: cd 04-code/ch21 && python3 real_judge.py --live   (after a provider client is wired)")
print(f"  inputs:  {len(dev)} development + {len(test)} held-out hardship offers (IDs in out/lab.json)")
print("  judges:  hardship-judge-v1; stated-change-judge-v1; permission-judge-v1 (with C-02, C-03, C-09 results)")
print("  reports: validation tables, admission, disagreement causes, construct profile on the 80 edits")
if "--live" not in sys.argv:
    print("  [RESULT PENDING: run `cd 04-code/ch21 && python3 real_judge.py --live` after a provider client is wired]")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "real_judge.json").write_text(json.dumps(
        {"status": "pending", "dev": len(dev), "test": len(test), "edits": 80, "temperature": 0}) + "\n")
    sys.exit(0)
raise SystemExit("No provider client is wired in this repository; add one in call() before running --live.")
