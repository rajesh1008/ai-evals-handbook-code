#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="../truss:${PYTHONPATH:-}"
python3 lab.py
python3 try_its.py
python3 - <<'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
tryits=json.loads(Path('out/try_its.json').read_text())
lines=[
 f"Chapter 43 lab OUTPUT (deterministic; no paid API)",
 f"digest={lab['digest']} seed={lab['seed']}",
 f"platforms={','.join(lab['platforms'])}",
 f"all_pinned_admit={lab['all_pinned_admit']} ceiling={lab['ceiling']}",
 f"inject platform={lab['inject']['platform']} gate_changed={lab['inject']['gate_changed']} extra_wrong={lab['inject']['extra_wrong_offers']}",
 f"try_its all_ok={tryits['all_ok']}",
 f"hosted_runs={lab['hosted_platform_runs']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
