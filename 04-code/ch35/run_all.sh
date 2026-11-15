#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py && python3 lab.py && python3 inject.py && python3 try_its.py
if [[ "${1:-}" == "--live" ]]; then python3 real_outcome_cue.py --live; else python3 real_outcome_cue.py || true; fi
python3 - <<'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
inj=json.loads(Path('out/inject.json').read_text())
real=json.loads(Path('out/real_outcome_cue.json').read_text()) if Path('out/real_outcome_cue.json').exists() else {}
lines=[
'Ch35 OUTPUT — From Offline Scores to Online Outcomes',
f"digest={lab['digest']} seed={lab['seed']} SIMULATED",
f"fee_recontact={lab['fee_recontact']}",
f"tone_recontact={lab['tone_recontact']}",
f"teaching={lab['teaching']}",
f"injection={lab['injection']}",
f"surrogacy_usable={lab['surrogacy']['usable_proxies']}",
]
if real: lines.append(f"REAL status={real.get('status')} correct={real.get('correct')}/{real.get('n')}")
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
