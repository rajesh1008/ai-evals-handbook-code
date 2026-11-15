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
  f"digest={ep['digest']} seed={ep['seed']} SIMULATED n_traces={ep['n_traces']}",
  f"winner_findings={ep['winner_findings']} winner_vocabulary={ep['winner_vocabulary']} inversion={ep['inversion']}",
  f"inject_caught={inj['caught']} failure={inj['failure']}",
  f"record_sha12={lab['record']['record_sha12']}",
  f"live_provider_eval_sweeps={ep['live_provider_eval_sweeps']} paid_calls={ep['paid_calls']}",
]
# scores
for r in ep['rows']:
  lines.append(f"candidate_{r['candidate']}_findings={r['findings']['score']}_vocab={r['vocabulary']['score']}")
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
