#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 real_shadow.py || true
python3 - <<'PY'
import json
from pathlib import Path
out=Path('out')
lab=json.loads((out/'lab.json').read_text())
inj=json.loads((out/'inject.json').read_text())
real=json.loads((out/'real_shadow.json').read_text()) if (out/'real_shadow.json').exists() else {}
lines=['Chapter 38 OUTPUT',
f"digest {lab['digest']}",
f"overall {lab['overall_pct']}% hardship {lab['hardship_pct']}%",
f"exit_met {lab['exit']['met']} decision {lab['exit']['decision']}",
f"inject_caught {inj['caught']} tool {inj['tool']}",
f"real REAL {real.get('n_ok','?')}/{real.get('n','?')}"]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
