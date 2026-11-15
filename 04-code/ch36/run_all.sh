#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 real_ab.py || true
python3 - <<'PY'
import json
from pathlib import Path
out=Path('out')
lab=json.loads((out/'lab.json').read_text())
inj=json.loads((out/'inject.json').read_text())
real=json.loads((out/'real_ab.json').read_text()) if (out/'real_ab.json').exists() else {}
lines=[
'Chapter 36 OUTPUT',
f"digest {lab['digest']}",
f"assignment control={lab['assignment']['n_control']} treatment={lab['assignment']['n_treatment']}",
f"interleave_winner {lab['interleave']['winner']}",
f"inject_caught {inj['caught']} k={inj['k_errors']} n={inj['n']} arm={inj['arm_stopped']}",
f"real REAL {real.get('n_ok','?')}/{real.get('n','?')}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
