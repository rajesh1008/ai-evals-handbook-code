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
 f"Chapter 44 lab OUTPUT (deterministic; no paid API)",
 f"digest={lab['digest']} seed={lab['seed']}",
 f"n={lab['n']} vendor_claim={lab['vendor_claim_rate']}",
 f"wrong={lab['receipt']['wrong_offers']} rate={lab['receipt']['rate']:.4f} wilson_upper={lab['receipt']['wilson_upper']:.4f} admit={lab['receipt']['admit']}",
 f"inject overlap={lab['inject']['overlap_count']} rate_moved={lab['inject']['rate_moved_toward_claim']} decline={lab['decline_purchase']}",
 f"try_its all_ok={tryits['all_ok']}",
 f"live_vendor_http={lab['live_vendor_http']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
