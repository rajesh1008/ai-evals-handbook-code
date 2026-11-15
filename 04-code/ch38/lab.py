from __future__ import annotations
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'truss'))
from truss.shadow import agreement_report, exit_rule_eval, disagreement_sample, shadow_run_record, shadow_tool_call

OUT=Path(__file__).parent/'out'

def main():
    fix=json.loads((OUT/'fixture.json').read_text())
    rep=agreement_report(fix['rows'])
    slices={k:v['rate'] for k,v in rep['by_slice'].items()}
    exit_r=exit_rule_eval(rep['overall'], slices, fix['exit_floors'])
    sample=disagreement_sample(fix['rows'], limit=15)
    # safe dry-run call
    safe=shadow_tool_call('draft_offer_preview', fix['dry_run_allowlist'], execute=False)
    rec=shadow_run_record(fix['run_id'], fix['candidate_pin'], fix['n'], fix['dry_run_allowlist'], fix['exit_floors'])
    out={
        "kind":"SIMULATED","digest":fix["digest"],"seed":fix["seed"],
        "report":rep,"exit":exit_r,"disagreement_sample_n":len(sample),
        "safe_tool":safe,"record":rec,
        "overall_pct":round(rep['overall']*100,1),
        "hardship_pct":round(slices.get('hardship',0)*100,1),
        "study_window":fix["study_window"],
    }
    (OUT/'lab.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({k:out[k] for k in ('digest','overall_pct','hardship_pct','exit')},indent=2))

if __name__=='__main__':
    main()
