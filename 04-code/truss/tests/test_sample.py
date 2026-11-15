from collections import Counter

from truss.sample import stratified_sample
from truss.store import open_store

QUOTAS = {"hardship": 100, "fee_explanation": 70, "account_question": 40,
          "payoff_letter": 35, "lien_release": 30, "statement_request": 25}


def test_quotas_met_and_reproducible():
    db = open_store()
    a = stratified_sample(db, QUOTAS)
    b = stratified_sample(db, QUOTAS)
    assert a == b and len(a) == 300 and len(set(a)) == 300
    flows = Counter(db.execute(f"SELECT flow FROM traces WHERE trace_id = '{t}'").fetchone()[0]
                    for t in a)
    assert flows == Counter(QUOTAS)


def test_store_is_read_only():
    db = open_store()
    try:
        db.execute("DELETE FROM traces")
    except Exception as e:
        assert "readonly" in str(e)
    else:
        raise AssertionError("trace store accepted a write")
