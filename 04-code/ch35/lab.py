from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'truss'))
from truss.onlinecorr import (
    correlate_proxy_online, surrogacy_table, counterfactual_log,
    anti_correlation_injection, online_signal_rates, ONLINE_SIGNALS,
)
OUT=Path(__file__).parent/'out'

def main():
    fix=json.loads((OUT/'fixture.json').read_text())
    rows=fix['rows']
    fee=[r['fee_offline'] for r in rows]
    tone=[r['tone_offline'] for r in rows]
    rc=[r['re_contact'] for r in rows]
    comp=[r['complaint'] for r in rows]
    fee_rc=correlate_proxy_online(fee, rc, name='fee_explanation', signal='re_contact')
    # For prediction of harm, negative r is good (higher fee → lower recontact)
    fee_rc['predicts']=fee_rc['r'] <= -0.35
    fee_rc['useful_direction']='higher_offline_lower_recontact'
    tone_rc=correlate_proxy_online(tone, rc, name='tone', signal='re_contact')
    tone_rc['predicts']=abs(tone_rc['r']) >= 0.35
    tone_comp=correlate_proxy_online(tone, comp, name='tone', signal='complaint')
    table=surrogacy_table([fee_rc, tone_rc, tone_comp])
    # Harbor teaching: fee predicts; tone does not
    teaching={
        'fee_predicts_recontact': fee_rc['predicts'] and fee_rc['r'] < 0,
        'tone_predicts_nothing': abs(tone_rc['r']) < 0.35,
    }
    inj=anti_correlation_injection(fix['injection']['delight'], fix['injection']['complaints'])
    cf=counterfactual_log('t-350101', shown_arm='fee_prompt_v3', logged_alt_arms=['fee_prompt_v2'], policy_hash='pol-9c2a')
    # aggregate online rates from last week proxies as counts
    rates=online_signal_rates({
        'resolution': int(sum(r['resolution'] for r in rows)*10),
        're_contact': int(sum(rc)*100),
        'escalation': int(sum(r['escalation'] for r in rows)*100),
        'complaint': int(sum(comp)*100),
    }, n_sessions=1000)
    out={
        'seed': fix['seed'], 'digest': fix['digest'], 'simulated': True,
        'fee_recontact': fee_rc, 'tone_recontact': tone_rc, 'tone_complaint': tone_comp,
        'surrogacy': table, 'teaching': teaching, 'injection': inj,
        'counterfactual': cf, 'online_rates': rates, 'signals': list(ONLINE_SIGNALS),
        'study_window': fix['study_window'], 'scoreboard_date': fix['scoreboard_date'],
    }
    (OUT/'lab.json').write_text(json.dumps(out, indent=2))
    print(json.dumps({
        'digest': out['digest'],
        'fee_r': fee_rc['r'], 'tone_r': tone_rc['r'],
        'teaching': teaching, 'injection': inj['label'],
    }, indent=2))
if __name__=='__main__':
    main()
