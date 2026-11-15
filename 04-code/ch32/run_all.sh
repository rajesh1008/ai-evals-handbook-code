#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
if [[ "${1:-}" == "--live" ]]; then
  python3 real_repeat_cue.py --live
else
  python3 real_repeat_cue.py || true
fi
python3 - <<'PY'
import json
from pathlib import Path
out=Path('out')
lab=json.loads((out/'lab.json').read_text())
inj=json.loads((out/'inject.json').read_text())
real=json.loads((out/'real_repeat_cue.json').read_text()) if (out/'real_repeat_cue.json').exists() else {}
lines=[]
lines.append('Ch32 OUTPUT — Variance, Repeats and the Noise Floor')
lines.append(f"digest={lab['digest']} seed={lab['seed']} SIMULATED suite")
lines.append(f"hardship scores={lab['hardship']['scores']} mean={lab['hardship']['mean']:.2f} sd={lab['hardship']['sd']:.3f}")
lines.append(f"fee scores={lab['fee']['scores']} mean={lab['fee']['mean']:.2f}")
lines.append(f"measured_floor={lab['measured_noise_floor_pts']} published_floor={lab['published_noise_floor_pts']} margin={lab['margin_pts']} threshold={lab['gate_threshold_pts']}")
lines.append(f"pass@k={lab['pass_contrast']['pass_at_k']:.3f} pass^k={lab['pass_contrast']['pass_hat_k']:.3f} n_tasks={lab['pass_contrast']['n_tasks']} k={lab['pass_contrast']['k']}")
lines.append(f"inside_floor={lab['inside_floor_diag']['label']} outside_floor={lab['outside_floor_diag']['label']}")
lines.append(f"inject correct_noise={inj['correct_call_is_noise']} naive_alarm={inj['naive_calls_regression']}")
if real:
    lines.append(f"REAL status={real.get('status')} correct={real.get('correct')}/{real.get('n')} model={real.get('model')}")
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
