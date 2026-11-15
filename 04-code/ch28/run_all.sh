#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
if [[ "${1:-}" == "--live" ]]; then python3 real_review_cue.py --live; else python3 real_review_cue.py || true; fi
{
  echo "=== Chapter 28 OUTPUT ==="
  echo "date: $(TZ=Asia/Calcutta date -Iseconds)"
  python3 -c "import sys; sys.path.insert(0,'../truss'); import truss; print('truss', truss.__version__)"
  echo "--- fixture ---"; python3 -c "import json; d=json.load(open('out/fixture.json')); print({k:d[k] for k in d if k!='rows'})"
  echo "--- lab ---"; python3 -c "import json; d=json.load(open('out/lab.json')); print({k:d[k] for k in d if k not in ('per_reviewer','fatigue')}); print('per', d['per_reviewer']); print('fatigue', d['fatigue'])"
  echo "--- inject ---"; cat out/inject.json
  echo "--- try_its ---"; cat out/try_its.json
  echo "--- real_review_cue ---"; python3 -c "import json; d=json.load(open('out/real_review_cue.json')); print({k:d[k] for k in d if k!='rows'})" 2>/dev/null || echo pending
} | tee OUTPUT.txt
