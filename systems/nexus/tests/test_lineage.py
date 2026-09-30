from dataclasses import replace
from nexus.lineage import DerivationRecord


def test_derivation_record_is_order_independent_and_tamper_evident():
    kwargs=dict(
        product_id='NEXUS:X',
        product_version='2',
        decision_ns=10,
        spec_hash='f'*64,
        code_version='0.2',
        parameters={'z':1},
    )
    a=DerivationRecord.create(input_hashes={'b':'2'*64,'a':'1'*64},**kwargs)
    b=DerivationRecord.create(input_hashes={'a':'1'*64,'b':'2'*64},**kwargs)
    assert a.derivation_hash==b.derivation_hash
    assert a.verify()
    assert not replace(a,decision_ns=11).verify()
