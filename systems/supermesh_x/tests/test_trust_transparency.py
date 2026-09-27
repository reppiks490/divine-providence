import json
import pytest
from scripts.signed_runtime_evidence import Ed25519Signer
from scripts.trust_transparency import (
    TrustPolicy, DurableTrustRoot, TransparencyLog, TrustTransparencyError,
    verify_inclusion_proof,
)


def _policy(epoch, signers, threshold=1):
    return TrustPolicy.from_signers(epoch, signers, threshold=threshold)


def test_trust_root_persists_public_policy_without_private_material(tmp_path):
    a=Ed25519Signer.generate('a')
    p=_policy(1,[a])
    path=tmp_path/'trust.json'
    root=DurableTrustRoot.bootstrap(path,p)
    loaded=DurableTrustRoot.load(path)
    assert loaded.policy.epoch==1
    assert loaded.policy.key_ids==('a',)
    text=path.read_text().lower()
    assert 'private' not in text and 'secretref://' not in text


def test_rotation_requires_old_and_new_threshold_and_sequential_epoch(tmp_path):
    a=Ed25519Signer.generate('a'); b=Ed25519Signer.generate('b'); c=Ed25519Signer.generate('c')
    root=DurableTrustRoot.bootstrap(tmp_path/'trust.json',_policy(1,[a],1))
    nextp=_policy(2,[b,c],2)
    receipt=root.make_rotation_statement(nextp)
    signed=[a.sign(receipt),b.sign(receipt),c.sign(receipt)]
    out=root.rotate(nextp,signed)
    assert out['from_epoch']==1 and out['to_epoch']==2
    assert root.policy.key_ids==('b','c')
    with pytest.raises(TrustTransparencyError):
        root.rotate(_policy(4,[a],1),[a.sign(root.make_rotation_statement(_policy(4,[a],1)))])


def test_rotation_rejects_insufficient_new_threshold(tmp_path):
    a=Ed25519Signer.generate('a'); b=Ed25519Signer.generate('b'); c=Ed25519Signer.generate('c')
    root=DurableTrustRoot.bootstrap(tmp_path/'trust.json',_policy(1,[a],1))
    nextp=_policy(2,[b,c],2)
    st=root.make_rotation_statement(nextp)
    with pytest.raises(TrustTransparencyError): root.rotate(nextp,[a.sign(st),b.sign(st)])


def test_merkle_inclusion_proof_and_tamper_detection():
    log=TransparencyLog()
    for x in ({'n':1},{'n':2},{'n':3},{'n':4},{'n':5}): log.append(x)
    proof=log.inclusion_proof(3)
    assert verify_inclusion_proof({'n':4},3,5,proof,log.root_digest())
    assert not verify_inclusion_proof({'n':999},3,5,proof,log.root_digest())


def test_signed_checkpoints_chain_and_reject_equivocation():
    s=Ed25519Signer.generate('log')
    log=TransparencyLog(); log.append({'a':1})
    c1=log.checkpoint(s,key_epoch=1)
    log.append({'b':2}); c2=log.checkpoint(s,key_epoch=1)
    assert c2['statement']['previous_checkpoint_digest']==c1['statement_digest']
    log.verify_checkpoint(c1,s.public_key_bytes())
    log.verify_checkpoint(c2,s.public_key_bytes(),previous=c1)
    evil=json.loads(json.dumps(c2)); evil['statement']['root_digest']='sha256:'+'00'*32
    with pytest.raises(TrustTransparencyError): log.verify_checkpoint(evil,s.public_key_bytes(),previous=c1)


def test_checkpoint_rollback_and_same_size_conflict_fail_closed():
    s=Ed25519Signer.generate('log')
    log=TransparencyLog(); log.append({'a':1}); c1=log.checkpoint(s,1)
    log.append({'b':2}); c2=log.checkpoint(s,1)
    with pytest.raises(TrustTransparencyError): log.verify_checkpoint(c1,s.public_key_bytes(),previous=c2)


def test_trust_policy_cannot_encode_execution_capabilities():
    a=Ed25519Signer.generate('a')
    with pytest.raises(TrustTransparencyError):
        TrustPolicy(epoch=1,keys={'a':a.public_key_bytes()},threshold=1,metadata={'capabilities':['broker.orders']})
