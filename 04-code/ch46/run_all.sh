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
a4=lab['artefacts']['A4_outcome_analysis']
lines=[
  f"kind={lab['kind']} seed={lab['seed']} pack_sha12={lab['pack_sha12']}",
  f"table_sha12={lab['table_sha12']}",
  f"ch45_digest_ref=af63808723f1 record_ref=3d4c15e44e50",
  f"pre_overall k={a4['overall_pre']['k']} wilson_hi={a4['overall_pre']['wilson_hi']:.4f} OPEN={a4['overall_pre']['OPEN']}",
  f"post_overall k={a4['overall_post']['k']} wilson_hi={a4['overall_post']['wilson_hi']:.4f} OPEN={a4['overall_post']['OPEN']}",
  f"hot={a4['hot_segment']} pre_hi={a4['hot_pre']['wilson_hi']:.4f} post_hi={a4['hot_post']['wilson_hi']:.4f}",
  f"metric_drift_caught={inj['caught']} mismatches={inj['mismatch_count']}",
  f"returned_artefact={lab['returned_artefact']['id']}",
  f"artefacts={','.join(lab['artefact_order'])}",
  f"sr26_2_genai_excluded={lab['artefacts']['A7_limitations_pending_scope']['sr26_2_generative_agentic_excluded']}",
  f"live_pending={lab['artefacts']['A7_limitations_pending_scope']['live_provider_batteries']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
