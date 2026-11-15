from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'truss'))
from truss.governance import (
    build_manifest, reexecute_from_manifest, redaction_signal_check,
    retention_job, residency_tag, gold_access_record, eval_inventory,
)
OUT=Path(__file__).parent/'out'
FIX=json.loads((OUT/'fixture.json').read_text())
cases=FIX['cases']
man=build_manifest(
    run_id='run-2028-09-20-hardship',
    model_pin='compass-hardship-2028-08-b',
    prompt_digest='p3feedee0001',
    dataset_digest=FIX['digest'],
    seed=2033,
    suite='hardship-fee-v4',
    created_at='2028-09-20',
    residency='us-west',
    owner='Ryan Mitchell',
)
# six-month-old re-exec: old manifest vs available (dataset digest changed)
old=FIX['old_manifest']
# attach digest field as build would
old_full=build_manifest(**old)
replay=reexecute_from_manifest(old_full, FIX['available_now'])
# retention
ret=retention_job(cases, retain_days=FIX['retain_days'], as_of_day=400)
# redaction on raw vs redacted views
raw_rows=[{'case_id':c['case_id'],'fee_amount':c['fee_amount']} for c in cases[:50]]
red_rows=[{'case_id':c['case_id'],'fee_amount':c['fee_amount_redacted']} for c in cases[:50]]
red_ok=redaction_signal_check(raw_rows, metric_fields=['fee_amount'], redacted_fields=['loan_token'])
red_bad=redaction_signal_check(red_rows, metric_fields=['fee_amount'], redacted_fields=['fee_amount','loan_token'])
res=residency_tag('eu-central', FIX['allowed_regions'])
access=[gold_access_record('Diane Porter','gold_owner','read','e-340101','2028-09-20T10:00:00Z'),
        gold_access_record('vendor-annotator','vendor','deny','e-340101','2028-09-20T10:05:00Z')]
inv=eval_inventory([
    {'artefact':'hardship gold','location':'vault://gold/hardship','owner':'Diane Porter','residency':'us-west','retention_days':365},
    {'artefact':'fee traces','location':'truss://traces/fee','owner':'Ryan Mitchell','residency':'us-west','retention_days':180},
    {'artefact':'judge outputs','location':'truss://judges/fee','owner':'Ryan Mitchell','residency':'us-west','retention_days':180},
])
out={'kind':'SIMULATED','digest':FIX['digest'],'manifest':man,'old_replay':replay,'retention':ret,
     'redaction_ok':red_ok,'redaction_inject':red_bad,'residency_eu':res,'access':access,'inventory':inv,
     'retire_rate':ret['retire_rate']}
(OUT/'lab.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'manifest':man['manifest_digest'],'replay_ok':replay['ok'],'retire_rate':round(ret['retire_rate'],3),
                  'red_ok':red_ok['signal_ok'],'red_inject_ok':red_bad['signal_ok'],'eu_ok':res['ok']},indent=2))
