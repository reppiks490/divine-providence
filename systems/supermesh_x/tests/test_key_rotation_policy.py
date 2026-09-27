import pytest
from scripts.key_rotation_policy import KeyRotationPolicy, verify_with_rotation, rotation_receipt, RotationError
from scripts.signed_health_state import sign_health_snapshot
K1=b'a'*32; K2=b'b'*32

def row(seq=2, epoch=10): return {'provider':'exa','health':.9,'circuit':'closed','sequence':seq,'epoch':epoch}

def test_overlap_accepts_previous_until_cutover_then_rejects():
    old=sign_health_snapshot(row(), key=K1, key_id='k1')
    p=KeyRotationPolicy(active_key_id='k2', previous_key_id='k1', overlap_until_epoch=10, revoked_key_ids=frozenset())
    assert verify_with_rotation(old, keys={'k1':K1,'k2':K2}, policy=p)['key_id']=='k1'
    late=sign_health_snapshot(row(epoch=11), key=K1, key_id='k1')
    with pytest.raises(RotationError): verify_with_rotation(late, keys={'k1':K1,'k2':K2}, policy=p)

def test_revocation_wins_even_during_overlap():
    old=sign_health_snapshot(row(), key=K1, key_id='k1')
    p=KeyRotationPolicy('k2','k1',99,frozenset({'k1'}))
    with pytest.raises(RotationError): verify_with_rotation(old, keys={'k1':K1,'k2':K2}, policy=p)

def test_unlisted_key_rejected_even_if_secret_present():
    rogue=sign_health_snapshot(row(), key=K1, key_id='rogue')
    p=KeyRotationPolicy('k2','k1',99,frozenset())
    with pytest.raises(RotationError): verify_with_rotation(rogue, keys={'rogue':K1,'k1':K1,'k2':K2}, policy=p)

def test_rotation_receipt_is_secret_free_and_deterministic():
    p=KeyRotationPolicy('k2','k1',10,frozenset({'k0'}))
    a=rotation_receipt(p, event='activate', epoch=10); b=rotation_receipt(p,event='activate',epoch=10)
    assert a==b and 'secret' not in str(a).lower() and 'key_material' not in str(a).lower()
    assert len(a['receipt_sha256'])==64
