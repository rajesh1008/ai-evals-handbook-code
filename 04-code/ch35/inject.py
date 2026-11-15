from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'truss'))
from truss.onlinecorr import anti_correlation_injection
OUT=Path(__file__).parent/'out'

def main():
    fix=json.loads((OUT/'fixture.json').read_text())
    lab=json.loads((OUT/'lab.json').read_text())
    inj=anti_correlation_injection(fix['injection']['delight'], fix['injection']['complaints'])
    out={
        'simulated': True,
        'injection': inj,
        'would_gate_on_delight': True,
        'correct_action': 'refuse_gate',
        'lesson': inj['lesson'],
        'contrast_fee_r': lab['fee_recontact']['r'],
    }
    (OUT/'inject.json').write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
if __name__=='__main__':
    main()
