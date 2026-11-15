#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 - <<'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
inj=json.loads(Path('out/inject.json').read_text())
ep=lab['evidence_pack']
lines=[
  f"digest={ep['digest']} seed=2045 SIMULATED n={ep['n']}",
  f"target_wrong_offer={ep['target']}",
  f"pre_overall k={ep['pre_overall']['k']} rate={ep['pre_overall']['rate']:.4f} wilson_hi={ep['pre_overall']['wilson_hi']:.4f} OPEN={ep['pre_overall']['OPEN']}",
  f"post_overall k={ep['post_overall']['k']} rate={ep['post_overall']['rate']:.4f} wilson_hi={ep['post_overall']['wilson_hi']:.4f} OPEN={ep['post_overall']['OPEN']}",
  f"hot_segment={ep['hot_segment_pre']['segment']} pre_hi={ep['hot_segment_pre']['wilson_hi']:.4f} post_hi={ep['hot_segment_post']['wilson_hi']:.4f}",
  f"proxy_caught={inj['caught']} field={inj['illegal_proxy']}",
  f"record_sha12={lab['record']['record_sha12']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
