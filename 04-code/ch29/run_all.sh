#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 real_upgrade.py ${1:-}
python3 - <<'PY'
import json
from pathlib import Path
out = Path("out")
lab = json.loads((out/"lab.json").read_text())
inj = json.loads((out/"inject.json").read_text())
real = json.loads((out/"real_upgrade.json").read_text())
lines = [
  "Chapter 29 OUTPUT",
  f"digest {lab['digest']}",
  f"text {lab['text_delta']['baseline_pass_rate']:.3f} -> {lab['text_delta']['candidate_pass_rate']:.3f} (regress {lab['text_delta']['n_regress']})",
  f"tool {lab['tool_delta']['baseline_pass_rate']:.3f} -> {lab['tool_delta']['candidate_pass_rate']:.3f} (regress {lab['tool_delta']['n_regress']})",
  f"silent schema fails {lab['schema_silent_v2']['n_fail']} / pass_rate {lab['schema_silent_v2']['pass_rate']:.3f}",
  f"rot stale {lab['rot']['n_stale']} / {lab['rot']['n']}",
  f"decision {lab['experiment']['decision']} plant {lab['regression_caught']}",
  f"inject text_pass={inj['text_metrics_pass']} ship={inj['ships_with_tool_gate']}",
  f"real {real['kind']} {real['n_ok']}/{real['n']} ({real['rate']:.3f})",
]
Path("OUTPUT.txt").write_text("\n".join(lines)+"\n")
print("\n".join(lines))
PY
