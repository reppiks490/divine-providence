import pytest
from scripts.signed_runtime_evidence import Ed25519Signer, TrustStore, SignedEvidenceJournal, SignatureError


def test_canonical_signature_verifies_and_tamper_fails():
    signer=Ed25519Signer.generate('k1')
    trust=TrustStore(); trust.add('k1', signer.public_key_bytes())
    env=signer.sign({'run_id':'r1','fencing_token':7,'kind':'launch','payload':{'b':2,'a':1}})
    assert trust.verify(env)['key_id']=='k1'
    env['statement']['payload']['a']=9
    with pytest.raises(SignatureError): trust.verify(env)


def test_unknown_wrong_and_revoked_keys_fail_closed_and_rotation_works():
    a=Ed25519Signer.generate('a'); b=Ed25519Signer.generate('b')
    trust=TrustStore(); trust.add('a',a.public_key_bytes())
    with pytest.raises(SignatureError): trust.verify(b.sign({'run_id':'r','fencing_token':1,'kind':'x','payload':{}}))
    trust.add('b',b.public_key_bytes()); assert trust.verify(b.sign({'run_id':'r','fencing_token':1,'kind':'x','payload':{}}))
    trust.revoke('b')
    with pytest.raises(SignatureError): trust.verify(b.sign({'run_id':'r','fencing_token':2,'kind':'x','payload':{}}))
    with pytest.raises(SignatureError): trust.add('b',b.public_key_bytes())


def test_signed_journal_rejects_replay_stale_fence_and_run_mismatch():
    s=Ed25519Signer.generate('k'); t=TrustStore(); t.add('k',s.public_key_bytes())
    j=SignedEvidenceJournal('r1',t)
    e=s.sign({'run_id':'r1','fencing_token':4,'kind':'launch','payload':{'provider':'p'}})
    assert j.admit(e)['kind']=='signed:launch'
    with pytest.raises(SignatureError): j.admit(e)
    with pytest.raises(SignatureError): j.admit(s.sign({'run_id':'r1','fencing_token':3,'kind':'heartbeat','payload':{}}))
    with pytest.raises(SignatureError): j.admit(s.sign({'run_id':'r2','fencing_token':5,'kind':'heartbeat','payload':{}}))


def test_signature_never_confers_authority():
    s=Ed25519Signer.generate('k'); t=TrustStore(); t.add('k',s.public_key_bytes())
    j=SignedEvidenceJournal('r',t,allowed_capabilities={'runtime.inspect'})
    bad=s.sign({'run_id':'r','fencing_token':1,'kind':'claim','payload':{'capabilities':['runtime.inspect','broker.orders']}})
    with pytest.raises(SignatureError): j.admit(bad)
    good=s.sign({'run_id':'r','fencing_token':1,'kind':'claim','payload':{'capabilities':['runtime.inspect']}})
    assert j.admit(good)


def test_private_key_material_never_appears_in_envelope():
    s=Ed25519Signer.generate('k')
    env=s.sign({'run_id':'r','fencing_token':1,'kind':'x','payload':{}})
    text=repr(env).lower()
    assert 'private' not in text and 'secretref://' not in text
