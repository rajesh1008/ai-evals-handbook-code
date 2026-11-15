from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'truss'))
from truss.onlinecorr import correlate_proxy_online, counterfactual_log, online_signal_rates
OUT=Path(__file__).parent/'out'

def main():
    lab=json.loads((OUT/'lab.json').read_text())
    fix=json.loads((OUT/'fixture.json').read_text())
    fee=[r['fee_offline'] for r in fix['rows']]
    esc=[r['escalation'] for r in fix['rows']]
    c=correlate_proxy_online(fee, esc, name='fee', signal='escalation')
    cf=counterfactual_log('t-350199', shown_arm='a', logged_alt_arms=[], policy_hash='')
    rates=online_signal_rates({'resolution':800,'re_contact':120,'escalation':40,'complaint':30}, 1000)
    out={'try1_fee_escalation':c,'try2_incomplete_cf':cf,'try3_rates':rates,'simulated':True}
    (OUT/'try_its.json').write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
if __name__=='__main__':
    main()
