import pytest
from scripts.signed_health_state import sign_health_snapshot, verify_health_snapshot, VerificationError

KEY=b'k'*32

def base(seq=1, epoch=7):
    return {'provider':'exa','health':0.8,'circuit':'closed','sequence':seq,'epoch':epoch,'observed_at_ms':10}

def test_sign_and_verify_roundtrip_and_secret_free_receipt():
    signed=sign_health_snapshot(base(), key=KEY, key_id='health-k1')
    out=verify_health_snapshot(signed, keys={'health-k1':KEY}, minimum_epoch=7, last_sequence=0)
    assert out['provider']=='exa'
    assert 'key' not in signed and 'secret' not in signed
    assert len(signed['auth_tag'])==64

def test_tamper_rejected():
    signed=sign_health_snapshot(base(), key=KEY, key_id='health-k1')
    signed['health']=0.1
    with pytest.raises(VerificationError): verify_health_snapshot(signed, keys={'health-k1':KEY})

def test_replay_and_epoch_rollback_rejected():
    signed=sign_health_snapshot(base(seq=5,epoch=8), key=KEY, key_id='health-k1')
    with pytest.raises(VerificationError): verify_health_snapshot(signed, keys={'health-k1':KEY}, last_sequence=5)
    with pytest.raises(VerificationError): verify_health_snapshot(signed, keys={'health-k1':KEY}, minimum_epoch=9)

def test_key_rotation_accepts_known_key_id_and_rejects_unknown():
    signed=sign_health_snapshot(base(), key=KEY, key_id='health-k2')
    assert verify_health_snapshot(signed, keys={'health-k1':b'x'*32,'health-k2':KEY})['key_id']=='health-k2'
    with pytest.raises(VerificationError): verify_health_snapshot(signed, keys={'health-k1':KEY})

def test_domain_separation_blocks_cross_protocol_reuse():
    signed=sign_health_snapshot(base(), key=KEY, key_id='health-k1', domain='supermesh.health.v1')
    with pytest.raises(VerificationError): verify_health_snapshot(signed, keys={'health-k1':KEY}, domain='supermesh.audit.v1')
