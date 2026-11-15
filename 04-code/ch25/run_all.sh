#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
if [[ "${1:-}" == "--live" ]]; then
  python3 real_sim.py --live
else
  python3 real_sim.py || true
fi
{
  echo "=== Chapter 25 OUTPUT ==="
  echo "date: $(TZ=Asia/Calcutta date -Iseconds)"
  python3 -c "import sys; sys.path.insert(0,'../truss'); import truss; print('truss', truss.__version__)"
  echo "--- fixture ---"; python3 -c "import json; d=json.load(open('out/fixture.json')); print({k:d[k] for k in ['seed','n','digest','sim_goal_completion','real_goal_completion','named_polite','id_range']})"
  echo "--- lab ---"; python3 -c "import json; d=json.load(open('out/lab.json')); print({k:d[k] for k in d if k not in ('persona_table','fidelity','perturbation')}); print('perturbation', d['perturbation']['survive_rate_among_before_ok'])"
  echo "--- inject ---"; cat out/inject.json
  echo "--- try_its ---"; cat out/try_its.json
  echo "--- real_sim ---"; if [[ -f out/real_sim.json ]]; then python3 -c "import json; d=json.load(open('out/real_sim.json')); print({k:d[k] for k in d if k!='rows'})"; else echo pending; fi
} | tee OUTPUT.txt
