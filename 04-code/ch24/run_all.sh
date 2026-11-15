#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
if [[ "${1:-}" == "--live" ]]; then
  python3 real_judge.py --live
else
  python3 real_judge.py || true
fi
{
  echo "=== Chapter 24 OUTPUT ==="
  echo "date: $(TZ=Asia/Calcutta date -Iseconds)"
  python3 -c "import truss,sys; sys.path.insert(0,'../truss'); import truss; print('truss', truss.__version__)"
  echo "--- fixture ---"; python3 -c "import json; d=json.load(open('out/fixture.json')); print({k:d[k] for k in ['seed','n','digest','kind_counts','looped','named_lucky']})"
  echo "--- lab ---"; python3 -c "import json; print(json.dumps(json.load(open('out/lab.json')), indent=2)[:4000])"
  echo "--- inject ---"; cat out/inject.json
  echo "--- try_its ---"; cat out/try_its.json
  echo "--- judge ---"; if [[ -f out/judge.json ]]; then python3 -c "import json; d=json.load(open('out/judge.json')); print({k:d[k] for k in d if k!='rows'})"; else echo pending; fi
} | tee OUTPUT.txt
