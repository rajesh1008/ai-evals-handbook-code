#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="../truss:${PYTHONPATH:-}"
python3 fixture.py
python3 lab.py
python3 inject.py
python3 try_its.py
python3 - <<'PY'
import json
from pathlib import Path
lab=json.loads(Path("out/lab.json").read_text())
inj=json.loads(Path("out/inject.json").read_text())
try_its=json.loads(Path("out/try_its.json").read_text())
lines=[]
lines.append("Chapter 41 lab OUTPUT (deterministic; no paid API)")
lines.append(f"digest={lab['digest']} seed={lab['seed']}")
lines.append(f"Ch16 charged_usd={lab['ch16_verified']['charged_usd']} ceiling={lab['study_ceiling']['safe_ceiling_usd']}")
lines.append(f"request_ids={lab['ch16_verified']['request_ids']} commits={lab['ch16_verified']['ledger_commits']} orphans={lab['ch16_verified']['orphans']} rows={lab['ch16_verified']['jsonl_rows']} agent_turns={lab['ch16_verified']['agent_turns']}")
lines.append(f"waterfall {lab['waterfall']['start_usd']} -> {lab['waterfall']['end_usd']} saved={lab['waterfall']['saved_usd']} (SIMULATED)")
lines.append(f"inject admit={inj['gate']['admit']} failed_bias={inj['gate']['failed_bias_battery']}")
lines.append(f"try_its all_ok={try_its['all_ok']}")
lines.append(f"teaching={lab['teaching']}")
Path("OUTPUT.txt").write_text("\n".join(lines)+"\n")
print(Path("OUTPUT.txt").read_text())
PY
