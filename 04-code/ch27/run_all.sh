#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
if [[ "${1:-}" == "--live" ]]; then python3 real_authority.py --live; else python3 real_authority.py || true; fi
{
  echo "=== Chapter 27 OUTPUT ==="
  echo "date: $(TZ=Asia/Calcutta date -Iseconds)"
  python3 -c "import sys; sys.path.insert(0,'../truss'); import truss; print('truss', truss.__version__)"
  echo "--- fixture ---"; python3 -c "import json; d=json.load(open('out/fixture.json')); print({k:d[k] for k in ['seed','n','digest','kind_counts','named_forbidden']})"
  echo "--- lab ---"; python3 -c "import json; d=json.load(open('out/lab.json')); print(d['authority']); print('adv', d['adversarial']); print('incidents', d['incidents'])"
  echo "--- inject ---"; cat out/inject.json
  echo "--- try_its ---"; cat out/try_its.json
  echo "--- real_authority ---"; python3 -c "import json; d=json.load(open('out/real_authority.json')); print({k:d[k] for k in d if k!='rows'})" 2>/dev/null || echo pending
} | tee OUTPUT.txt
