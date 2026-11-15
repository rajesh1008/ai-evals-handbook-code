from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from truss.shadow import shadow_tool_call, exit_rule_eval
OUT=ROOT/'ch38'/'out'

def test_rates_and_hold():
    lab=json.loads((OUT/'lab.json').read_text())
    assert lab['digest']=='e69f6d2d56a6'
    assert lab['overall_pct']==96.1
    assert lab['hardship_pct']==88.0
    assert lab['exit']['met'] is False
    assert lab['exit']['decision']=='HOLD'

def test_injection_side_effect():
    inj=json.loads((OUT/'inject.json').read_text())
    assert inj['caught'] is True
    assert inj['tool']=='send_offer_sms'
    assert inj['result']['side_effect'] is True

def test_dry_run_blocks_without_execute():
    r=shadow_tool_call('send_offer_sms', ['get_balance'], execute=False)
    assert r['blocked'] is True and r['side_effect'] is False

def test_exit_rule_math():
    ex=exit_rule_eval(0.961, {'hardship':0.88}, {'overall':0.98,'hardship':0.95})
    assert ex['met'] is False and ex['decision']=='HOLD'
