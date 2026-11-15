#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 real_stats.py
python3 - <<'PY'
import json
from pathlib import Path
lab=json.loads(Path('out/lab.json').read_text())
inj=json.loads(Path('out/inject.json').read_text())
real=json.loads(Path('out/real_stats.json').read_text())
ci=lab['board_ci']
lines=[
 'Chapter 31 OUTPUT',
 f"digest {lab['digest']}",
 f"board {ci['k']}/{ci['n']} rate {ci['rate']:.4f} Wilson [{ci['lo']:.4f},{ci['hi']:.4f}] upper {lab['board_upper']['upper']:.4f}",
 f"n0_for_0.5pct {lab['n_zero_fail_for_0_5pct']} n_margin {lab['n_margin_0_5pct_pm_0_2pp']} victor_n {lab['victor_n']}",
 f"paired_diff {lab['paired']['point_diff']:.4f} CI [{lab['paired']['lo']:.4f},{lab['paired']['hi']:.4f}] includes0 {lab['paired']['includes_zero']}",
 f"inject unpaired_diff {inj['unpaired_best_diff']:.4f} erased {inj['erased']}",
 f"real {real['kind']} {real['n_ok']}/{real['n']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
