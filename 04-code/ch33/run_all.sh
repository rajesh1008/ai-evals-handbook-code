#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py && python3 lab.py && python3 inject.py && python3 try_its.py && python3 real_gov.py
python3 - <<'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text()); inj=json.loads(Path('out/inject.json').read_text()); real=json.loads(Path('out/real_gov.json').read_text())
lines=[
 'Chapter 33 OUTPUT',
 f"digest {lab['digest']}",
 f"manifest {lab['manifest']['manifest_digest']}",
 f"old_replay_ok {lab['old_replay']['ok']}",
 f"retire_rate {lab['retire_rate']:.3f}",
 f"redaction_inject_caught {inj['caught']} destroyed {inj['n_destroyed']}",
 f"real {real['kind']} {real['n_ok']}/{real['n']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))
PY
