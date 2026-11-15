#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 - <<'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
inj=json.loads(Path('out/inject.json').read_text())
ep=lab['evidence_pack']
lines=[
  f"digest={ep['digest']} seed={ep['seed']} SIMULATED n_configs={ep['n_configs']}",
  f"inject_config={ep['inject_config']} lint_pass={ep['inject_lint_pass']} gate={ep['inject_gate']} reason={ep['inject_reason']}",
  f"inject_caught={inj['caught']} failure={inj['failure']}",
  f"record_sha12={lab['record']['record_sha12']}",
  f"live_provider_eval_sweeps={ep['live_provider_eval_sweeps']} paid_calls={ep['paid_calls']}",
  f"ch16_ceiling_sum={ep['ch16_ceiling_sum']} kinds_unchanged={ep['ch16_ceiling_kinds_unchanged']}",
]
for r in ep['rows']:
  lines.append(f"config_{r['lint']['config']}_lint={r['lint']['lint_pass']}_gate={r['gate']['gate_result']}")
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
