from scripts.cross_runtime_vectors import canonical_json_bytes, ed25519_signature_vector, verify_signature_vector

def test_canonical_json_profile_is_runtime_stable():
    obj={'z':1,'a':['é',{'b':False,'a':None}]}
    assert canonical_json_bytes(obj)==b'{"a":["\\u00e9",{"a":null,"b":false}],"z":1}'

def test_ed25519_vector_is_deterministic_and_verifiable():
    seed='9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60'
    v=ed25519_signature_vector(seed, {})
    assert v['public_key_hex']=='d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a'
    assert v['canonical_hex']=='7b7d'
    assert v['signature_hex']=='b6f4132237e2fd27a45ced0d37d6df5bcbd07f640427afdcde5a4daa1aa1f76e7ff7824da58df2cbb013b217e3a5510491c2e4d7d4df210a0830648e6fdcfa0b'
    assert verify_signature_vector(v)
