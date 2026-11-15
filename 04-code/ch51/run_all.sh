#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 - << 'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
inj=json.loads(Path('out/inject.json').read_text())
ep=lab['evidence_pack']
lines=[
  'Ch51 OUTPUT — SIMULATED four teaching cases + Toronto offline/online mismatch',
  f"seed={ep['seed']} digest={lab['digest']} record={lab['record']['record_sha12']}",
  f"offline_pass={ep['offline']['pass_rate']} sliced_by_cycle_day={ep['offline']['sliced_by_cycle_day']}",
  f"online_edge_complaints={ep['online']['complaints']} root={ep['online']['root_cause']}",
  f"inject={inj['foreign']['verdict']} foreign_n={len(inj['foreign']['foreign_labels'])}",
  f"CH16_ceiling={ep['CH16']['ceiling_usd']} (kinds; not invoice)",
  'live_provider_sweeps=PENDING',
  'SIMULATED=True — teaching scenarios; not observed client history',
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
