#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 real_guard_cue.py --live || python3 real_guard_cue.py
python3 << 'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
inj=json.loads(Path('out/inject.json').read_text())
real=json.loads(Path('out/real_guard_cue.json').read_text())
lines=[
 f"Ch37 OUTPUT — Guardrails, Monitoring and Evals: One Family",
 f"digest={lab['digest']} seed={lab['seed']} SIMULATED",
 f"guards_promoted={len(lab['guards'])}",
 f"metrics={lab['metrics']}",
 f"vocab_overrefuse={lab['vocabulary']['overrefuse_rate']}",
 f"hardship_coverage={lab['hardship_coverage']['coverage']}",
 f"sms_break={inj['caught']}",
 f"REAL cues {real['correct']}/{real['n']} status={real['status']}",
 f"teaching={lab['teaching']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
