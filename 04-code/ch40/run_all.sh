#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="../truss:${PYTHONPATH:-}"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 <<'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
inj=json.loads(Path('out/inject.json').read_text())
tries=json.loads(Path('out/try_its.json').read_text())
page=Path('out/weekly_page.txt').read_text()
lines=[
 f"Ch40 OUTPUT — The Weekly Report",
 f"digest={lab['digest']} seed={lab['seed']} SIMULATED",
 f"weeks={lab['n_weeks']} hidden={lab['hide']['hidden']} caught={inj['caught']}",
 f"overall_delta={lab['overall_delta']:+.6f} hardship_delta={lab['hardship_delta']:+.6f}",
 f"decide={lab['decide_card']['failures']}/{lab['decide_card']['n']} wilson_hi={lab['decide_card']['wilson_hi']:.4f} meets={lab['decide_card']['meets_target']}",
 f"page_chars={lab['page_chars']}",
 f"try_its={[t['name'] for t in tries]}",
 f"teaching={lab['teaching']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
print('--- page head ---')
print('\n'.join(page.splitlines()[:20]))
PY
