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
lines=[
"Ch42 OUTPUT — Comparative Evals (SIMULATED)",
f"digest={lab['digest']} seed={lab['seed']} SIMULATED n_paired={lab['n_paired']}",
f"paired_ranking={lab['paired']['ranking']}",
f"unpaired_ranking={lab['unpaired_injection']['ranking']} reversed={lab['ranking_reversed']} caught={inj['caught']}",
f"slm_cost_ratio={lab['teaching']['slm_cost_ratio_vs_prompt']}",
f"router_gap={lab['router']['gap_to_oracle']:.3f} plateau={lab['router']['plateau_flag']}",
f"experiment_record={lab['experiment_record']['record_sha12']}",
f"n_comparisons={lab['multiple_comparison']['n_comparisons']} per_alpha={lab['multiple_comparison']['per_comparison_alpha']:.5f} structure={lab['multiple_comparison']['structure']}",
f"mcnemar_v2_slm_p={lab['paired_contrasts']['prompt_v2_vs_small_fee_model']['mcnemar']['p_value_exact']} discordant={lab['paired_contrasts']['prompt_v2_vs_small_fee_model']['table']['discordant']}",
f"mcnemar_v2_v1_p={lab['paired_contrasts']['prompt_v2_vs_prompt_v1']['mcnemar']['p_value_exact']}",
]
Path('OUTPUT.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
PY
