from dataclasses import replace
from nexus.lineage import DerivationRecord


def test_derivation_record_is_order_independent_and_tamper_evident():
    a=DerivationRecord.create(product_id='NEXUS:X',product_version='2',decision_ns=10,spec_hash='s',input_hashes={'b':'2','a':'1'},code_version='0.2',parameters={'z':1})
    b=DerivationRecord.create(product_id='NEXUS:X',product_version='2',decision_ns=10,spec_hash='s',input_hashes={'a':'1','b':'2'},code_version='0.2',parameters={'z':1})
    assert a.derivation_hash==b.derivation_hash
    assert a.verify()
    assert not replace(a,decision_ns=11).verify()
