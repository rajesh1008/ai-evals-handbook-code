#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
if [[ "${1:-}" == "--live" ]]; then python3 real_pr_cue.py --live; else python3 real_pr_cue.py || true; fi
python3 - <<'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
inj=json.loads(Path('out/inject.json').read_text())
real=json.loads(Path('out/real_pr_cue.json').read_text()) if Path('out/real_pr_cue.json').exists() else {}
lines=[
'Ch34 OUTPUT — Evals in the Pull Request',
f"digest={lab['digest']} seed={lab['seed']} SIMULATED",
f"candidate_fast={lab['candidate_fast']} candidate_slow={lab['candidate_slow']}",
f"teaching={lab['teaching']}",
f"ladder={lab['ladder']}",
f"inject_flake_blocks={inj['correct_release_blocked_by_flake']}",
f"median_days {lab['median_days_before']}->{lab['median_days_after']}",
f"cost_fast={lab['cost_fast_usd']['total_usd']} cost_slow={lab['cost_slow_usd']['total_usd']}",
]
if real: lines.append(f"REAL status={real.get('status')} correct={real.get('correct')}/{real.get('n')}")
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
