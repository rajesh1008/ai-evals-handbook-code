from truss.onlinecorr import pearson, correlate_proxy_online, anti_correlation_injection, counterfactual_log, surrogacy_table

def test_pearson_perfect():
    assert abs(pearson([1,2,3,4],[2,4,6,8])-1.0)<1e-9

def test_fee_like_negative():
    # synthetic
    xs=[0.9,0.8,0.7,0.6,0.5]; ys=[0.05,0.1,0.15,0.2,0.25]
    r=pearson(xs,ys)
    assert r < -0.9

def test_anti_injection():
    d=anti_correlation_injection([0.5,0.6,0.7,0.8,0.9],[0.1,0.15,0.2,0.25,0.3])
    assert d['label']=='BAD_PROXY'

def test_cf_complete():
    assert counterfactual_log('t', shown_arm='a', logged_alt_arms=['b'], policy_hash='h')['complete']
    assert not counterfactual_log('t', shown_arm='a', logged_alt_arms=[], policy_hash='')['complete']

def test_surrogacy_table():
    t=surrogacy_table([{'proxy':'fee','predicts':True},{'proxy':'tone','predicts':False}])
    assert t['signature']==8 and t['usable_proxies']==['fee']
