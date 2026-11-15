#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
if [[ "${1:-}" == "--live" ]]; then python3 real_incident_cue.py --live; else python3 real_incident_cue.py; fi
python3 << 'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
inj=json.loads(Path('out/inject.json').read_text())
real=json.loads(Path('out/real_incident_cue.json').read_text())
lines=[
"Ch39 OUTPUT — Incident to Eval: The Post-Mortem Loop",
f"digest={lab['digest']} seed={lab['seed']} SIMULATED",
f"median_tte_days={lab['median_tte_days']} before={lab['tte_before_days']}",
f"cases={len(lab['cases'])} sidebar_cases={lab['sidebar_cases']}",
f"weekly={lab['weekly']}",
f"symptom_injection_caught={inj['caught']}",
f"REAL cues {real['correct']}/{real['n']} status={real['status']}",
f"teaching={lab['teaching']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
