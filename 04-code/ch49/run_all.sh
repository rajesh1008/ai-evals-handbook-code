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
lines=[
  'Ch49 OUTPUT — SIMULATED Harbor Year-1 twelve-month ops',
  f"seed={lab['evidence_pack']['seed']} digest={lab['digest']} record={lab['record']['record_sha12']}",
  f"rollback_months={lab['evidence_pack']['scoreboard']['rollback_months']}",
  f"pin_verdict={lab['evidence_pack']['pin_diff']['verdict']} dual={lab['evidence_pack']['pin_diff']['dual_change']}",
  f"inject_single={inj['single']['verdict']} inject_dual={inj['dual']['verdict']}",
  f"CH16_ceiling={lab['evidence_pack']['CH16']['ceiling_usd']} (kinds; not invoice)",
  'live_provider_sweeps=PENDING',
  'SIMULATED=True — illustrative; not observed client history',
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
