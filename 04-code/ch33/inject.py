"""Failure injection: redaction removes fee amounts the metric needs."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'truss'))
from truss.governance import redaction_signal_check
OUT=Path(__file__).parent/'out'
FIX=json.loads((OUT/'fixture.json').read_text())
rows=[{'case_id':c['case_id'],'fee_amount':c['fee_amount_redacted']} for c in FIX['cases']]
r=redaction_signal_check(rows, metric_fields=['fee_amount'], redacted_fields=['fee_amount'])
out={'kind':'SIMULATED_INJECTION','name':'redact_fee_amount','signal_ok':r['signal_ok'],'n_destroyed':r['n_destroyed'],
     'overlap_removed':r['overlap_removed'],'caught': (not r['signal_ok'])}
(OUT/'inject.json').write_text(json.dumps(out,indent=2))
assert out['caught']
print(json.dumps(out,indent=2))
