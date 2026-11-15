from __future__ import annotations
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'truss'))
from truss.shadow import shadow_tool_call, exit_rule_eval

OUT=Path(__file__).parent/'out'

def main():
    allow=['get_balance']
    blocked=shadow_tool_call('send_offer_sms', allow, execute=False)
    ok=shadow_tool_call('get_balance', allow, execute=False)
    # exit with high floors fails
    ex=exit_rule_eval(0.961, {'hardship':0.88}, {'overall':0.98,'hardship':0.95})
    out={"blocked_without_execute":blocked["blocked"],"safe_ok":ok["ok"],"exit_met":ex["met"],"decision":ex["decision"]}
    (OUT/'try_its.json').write_text(json.dumps(out,indent=2))
    print(out)

if __name__=='__main__':
    main()
