"""Pending live run: score the frozen canary three times at temperature 0.

No model is called. When a provider key is available, this script should
send the forty frozen traces to the production judge three times with
temperature set to 0 and report the flip rate (traces whose verdict
moved at least once). The output replaces the [RESULT PENDING] sentence
in Chapter 19's monitoring section.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
print("=" * 100)
print("Pending live run: frozen canary x3 at temperature 0")
print("=" * 100)
print("  command: cd 04-code/ch19 && python3 real_judge.py")
print("  input:   forty pinned traces t-184901 to t-184940, fee-judge-v1 prompt")
print("  repeats: 3, temperature 0, same model pin")
print("  reports: per-trace verdicts, flip count, flip rate, majority table")
print("  [RESULT PENDING: run `cd 04-code/ch19 && python3 real_judge.py` after a provider client is wired]")
(HERE / "out").mkdir(exist_ok=True)
(HERE / "out" / "real_judge.json").write_text(
    '{"status": "pending", "n": 40, "repeats": 3, "temperature": 0}\n')
