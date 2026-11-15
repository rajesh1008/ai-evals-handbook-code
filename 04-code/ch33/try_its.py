from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'truss'))
from truss.governance import build_manifest, residency_tag
OUT=Path(__file__).parent/'out'
LAB=json.loads((OUT/'lab.json').read_text())
m=build_manifest(**{k:LAB['manifest'][k] for k in ['run_id','model_pin','prompt_digest','dataset_digest','seed','suite','created_at','residency','owner']})
assert m['manifest_digest']==LAB['manifest']['manifest_digest']
assert residency_tag('us-west',['us-west','us-east'])['ok']
out={'digest_match':True,'retire_rate':LAB['retire_rate']}
(OUT/'try_its.json').write_text(json.dumps(out,indent=2))
print(out)
