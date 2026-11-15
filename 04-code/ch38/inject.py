"""Failure injection: shadow calls a tool not on the dry-run allowlist with execute=True."""
from __future__ import annotations
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'truss'))
from truss.shadow import shadow_tool_call

OUT=Path(__file__).parent/'out'

def main():
    fix=json.loads((OUT/'fixture.json').read_text())
    # dangerous: send_offer_sms not in dry-run list, execute True
    bad=shadow_tool_call('send_offer_sms', fix['dry_run_allowlist'], execute=True)
    caught = bad.get('side_effect') is True and bad.get('error')=='tool_not_in_dry_run'
    out={
        "kind":"SIMULATED_INJECTION",
        "name":"shadow_tool_not_dry_run",
        "tool":"send_offer_sms",
        "result":bad,
        "caught":caught,
        "action":"abort_shadow_run",
    }
    (OUT/'inject.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':
    main()
