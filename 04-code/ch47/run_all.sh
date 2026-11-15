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
  f"digest={ep['digest']} seed={ep['seed']} SIMULATED n_week={ep['n_week']}",
  f"n_missed={ep['coverage']['n_missed']} ship={ep['ritual']['ship_verb']}",
  f"proxy_or_inject_caught={inj['caught']} missed_trace={inj['missed_trace_id']}",
  f"record_sha12={lab['record']['record_sha12']}",
  f"live_provider_eval_sweeps={ep['live_provider_eval_sweeps']}",
  f"traffic_share_teaching={ep['traffic_share_teaching']} prior={ep['prior_traffic_share']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
