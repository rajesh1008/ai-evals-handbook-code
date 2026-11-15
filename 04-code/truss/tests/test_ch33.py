from truss.governance import build_manifest, reexecute_from_manifest, redaction_signal_check, retention_job, residency_tag, eval_inventory
from truss import __version__

def test_version():
    assert int(__version__.split('.')[1]) >= 36

def test_manifest_replay():
    m=build_manifest(run_id='r',model_pin='a',prompt_digest='p',dataset_digest='d',seed=1,suite='s',created_at='t',residency='us-west',owner='o')
    assert 'manifest_digest' in m
    bad=reexecute_from_manifest(m,{**m,'dataset_digest':'other'})
    assert not bad['ok']

def test_redaction_retention_residency_inventory():
    r=redaction_signal_check([{'case_id':'1','fee_amount':'[REDACTED]'}], metric_fields=['fee_amount'], redacted_fields=['fee_amount'])
    assert not r['signal_ok']
    job=retention_job([{'case_id':'a','age_days':200},{'case_id':'b','age_days':10}], retain_days=180, as_of_day=400)
    assert job['n_retire']==1
    assert residency_tag('eu-central',['us-west'])['ok'] is False
    inv=eval_inventory([{'artefact':'g','location':'l','owner':'o','residency':'us-west','retention_days':30}])
    assert inv[0]['artefact']=='g'

def test_lab():
    import json
    from pathlib import Path
    p=Path(__file__).resolve().parents[2]/'ch33'/'out'/'lab.json'
    if not p.exists(): return
    d=json.loads(p.read_text())
    assert abs(d['retire_rate']-0.14)<0.02
    assert d['old_replay']['ok'] is False
