import json
import pytest
from recovery_auth import HMACRecoveryAuthenticator, HMACRecoveryKeyring
from recovery_asymmetric import (
    Ed25519RecoverySigner, Ed25519RecoveryKeyring,
    RecoveryTrustRootManifest, TrustRootKey,
)
from recovery_trust_root import (
    RecoveryTrustRootGeneration, RecoveryTrustRootAnchorAuthority,
    RecoveryTrustRootStore, RecoveryAlgorithmMode,
    MigrationAwareRecoveryAuthenticator,
)

H1=b'h'*32

def ed_bundle():
    prod=Ed25519RecoverySigner.generate('producer',key_id='ed1')
    policy=Ed25519RecoverySigner.generate('policy-root',key_id='policy')
    anchor=Ed25519RecoverySigner.generate('anchor-root',key_id='anchor')
    manifest=RecoveryTrustRootManifest.issue(
        producer_id='producer',
        producer_keys=(TrustRootKey.from_verifier(prod.verifier(),purpose='recovery-producer'),),
        policy_authority=TrustRootKey.from_verifier(policy.verifier(),purpose='policy-authority'),
    )
    return prod,policy,anchor,manifest

def make_store(tmp_path):
    prod,policy,anchor,manifest=ed_bundle()
    authority=RecoveryTrustRootAnchorAuthority(anchor)
    store=RecoveryTrustRootStore(tmp_path/'roots',authority)
    g1=RecoveryTrustRootGeneration.issue(
        generation=1,previous_generation_hash='0'*64,effective_recovery_generation=1,
        manifest=manifest,mode=RecoveryAlgorithmMode.HMAC_ONLY,
    )
    store.append(g1,fsync=False)
    return prod,anchor,manifest,store,g1

def test_anchor_chain_and_stale_head_replay_rejected(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    old_head=(tmp_path/'roots'/'HEAD').read_text()
    g2=RecoveryTrustRootGeneration.issue(
        generation=2,previous_generation_hash=g1.generation_hash,effective_recovery_generation=2,
        manifest=manifest,mode=RecoveryAlgorithmMode.DUAL,
    )
    store.append(g2,fsync=False)
    assert store.verify_chain().valid
    (tmp_path/'roots'/'HEAD').write_text(old_head)
    assert not store.verify_chain().valid

def test_root_manifest_substitution_rejected(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    p=tmp_path/'roots'/'trust-root-00000000000000000001.json'
    m=json.loads(p.read_text()); m['generation']['manifest']['producer_id']='evil'; p.write_text(json.dumps(m))
    assert not store.verify_chain().valid

def test_migration_mode_cannot_downgrade(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    g2=RecoveryTrustRootGeneration.issue(generation=2,previous_generation_hash=g1.generation_hash,
        effective_recovery_generation=2,manifest=manifest,mode=RecoveryAlgorithmMode.DUAL)
    store.append(g2,fsync=False)
    g3=RecoveryTrustRootGeneration.issue(generation=3,previous_generation_hash=g2.generation_hash,
        effective_recovery_generation=3,manifest=manifest,mode=RecoveryAlgorithmMode.ED25519_ONLY)
    store.append(g3,fsync=False)
    bad=RecoveryTrustRootGeneration.issue(generation=4,previous_generation_hash=g3.generation_hash,
        effective_recovery_generation=4,manifest=manifest,mode=RecoveryAlgorithmMode.HMAC_ONLY)
    with pytest.raises(ValueError): store.append(bad,fsync=False)

def test_skipping_dual_transition_rejected(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    bad=RecoveryTrustRootGeneration.issue(generation=2,previous_generation_hash=g1.generation_hash,
        effective_recovery_generation=2,manifest=manifest,mode=RecoveryAlgorithmMode.ED25519_ONLY)
    with pytest.raises(ValueError): store.append(bad,fsync=False)

def test_mixed_algorithm_history_and_post_migration_hmac_downgrade(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    hring=HMACRecoveryKeyring('producer',{'h1':H1},signing_key_id='h1')
    ering=Ed25519RecoveryKeyring('producer',{'ed1':prod.verifier()},signer=prod)
    auth=MigrationAwareRecoveryAuthenticator(hring,ering,store)
    e1=auth.sign({'generation':1,'x':'old'})
    assert e1.algorithm=='HMAC-SHA256' and auth.verify(e1)

    g2=RecoveryTrustRootGeneration.issue(generation=2,previous_generation_hash=g1.generation_hash,
        effective_recovery_generation=2,manifest=manifest,mode=RecoveryAlgorithmMode.DUAL)
    store.append(g2,fsync=False)
    e2=auth.sign({'generation':2,'x':'transition'})
    assert e2.algorithm=='Ed25519' and auth.verify(e1) and auth.verify(e2)

    g3=RecoveryTrustRootGeneration.issue(generation=3,previous_generation_hash=g2.generation_hash,
        effective_recovery_generation=3,manifest=manifest,mode=RecoveryAlgorithmMode.ED25519_ONLY)
    store.append(g3,fsync=False)
    e3=auth.sign({'generation':3,'x':'new'})
    assert e3.algorithm=='Ed25519' and auth.verify(e1) and auth.verify(e2) and auth.verify(e3)

    raw=HMACRecoveryAuthenticator('producer',H1,key_id='h1').sign({
        'generation':3,'trust_root_generation':3,'trust_root_hash':g3.generation_hash
    })
    assert not auth.verify(raw)

def test_wrong_trust_root_generation_or_hash_rejected(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    auth=MigrationAwareRecoveryAuthenticator(
        HMACRecoveryKeyring('producer',{'h1':H1},signing_key_id='h1'),
        Ed25519RecoveryKeyring('producer',{'ed1':prod.verifier()},signer=prod),store)
    e=auth.sign({'generation':1})
    payload=dict(e.payload); payload['trust_root_generation']=99
    bad=e.__class__(e.version,e.producer_id,e.algorithm,e.payload_hash,payload,e.signature,e.key_id)
    assert not auth.verify(bad)

def test_public_only_migration_verifier_cannot_sign(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    hverify=HMACRecoveryKeyring('producer',{'h1':H1},signing_key_id='h1')
    everify=manifest.recovery_keyring()
    auth=MigrationAwareRecoveryAuthenticator(hverify,everify,store,allow_hmac_signing=False)
    assert not auth.can_sign
    with pytest.raises(PermissionError): auth.sign({'generation':1})

def test_anchor_store_can_reopen_with_public_only_authority(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    verify_only=RecoveryTrustRootStore(tmp_path/'roots',RecoveryTrustRootAnchorAuthority(verifier=anchor.verifier()))
    assert verify_only.verify_chain().valid

def test_components_have_no_infrastructure_authority(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    auth=MigrationAwareRecoveryAuthenticator(
        HMACRecoveryKeyring('producer',{'h1':H1},signing_key_id='h1'),
        Ed25519RecoveryKeyring('producer',{'ed1':prod.verifier()},signer=prod),store)
    forbidden={'execute','mutate','promote','rollback','acquire','release'}
    for obj in [store,store.authority,auth]:
        assert forbidden.isdisjoint(dir(obj))

def test_signing_capability_uses_applicable_generation_not_future_head(tmp_path):
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    future=RecoveryTrustRootGeneration.issue(
        generation=2,previous_generation_hash=g1.generation_hash,
        effective_recovery_generation=100,manifest=manifest,mode=RecoveryAlgorithmMode.DUAL)
    store.append(future,fsync=False)
    auth=MigrationAwareRecoveryAuthenticator(
        HMACRecoveryKeyring('producer',{'h1':H1},signing_key_id='h1'),
        manifest.recovery_keyring(),store,allow_hmac_signing=True)
    assert auth.can_sign_for_generation(2)
    assert not auth.can_sign_for_generation(100)

def test_startup_history_crosses_hmac_dual_ed25519_without_downgrade(tmp_path):
    import dataclasses
    from durable_journal import DurableProofJournal
    from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
    from recovery_chain import AppendOnlyRecoveryChain
    from test_proof_journal import fixture

    journal=tmp_path/'proof.journal'; tx=fixture()
    DurableProofJournal(journal).append(dataclasses.asdict(tx),fsync=False)
    prod,anchor,manifest,store,g1=make_store(tmp_path)
    hring=HMACRecoveryKeyring('producer',{'h1':H1},signing_key_id='h1')
    ering=Ed25519RecoveryKeyring('producer',{'ed1':prod.verifier()},signer=prod)
    auth=MigrationAwareRecoveryAuthenticator(hring,ering,store)
    cfg=LoopConfig(
        durable_proof_journal_path=str(journal),startup_recovery_enabled=True,
        startup_recovery_now=20,recovery_chain_dir=str(tmp_path/'chain'),
        recovery_checkpoint_fsync=False,recovery_chain_lock_timeout_seconds=.01,
        recovery_authenticator=auth)

    first=InfrastructureSupervisoryLoop([],config=cfg)
    assert first._recovered_proof_transactions==()

    g2=RecoveryTrustRootGeneration.issue(
        generation=2,previous_generation_hash=g1.generation_hash,
        effective_recovery_generation=2,manifest=manifest,mode=RecoveryAlgorithmMode.DUAL)
    store.append(g2,fsync=False)
    second=InfrastructureSupervisoryLoop([],config=cfg)
    assert [x.transaction_hash for x in second._recovered_proof_transactions]==[tx.transaction_hash]

    g3=RecoveryTrustRootGeneration.issue(
        generation=3,previous_generation_hash=g2.generation_hash,
        effective_recovery_generation=3,manifest=manifest,mode=RecoveryAlgorithmMode.ED25519_ONLY)
    store.append(g3,fsync=False)
    third=InfrastructureSupervisoryLoop([],config=cfg)
    assert [x.transaction_hash for x in third._recovered_proof_transactions]==[tx.transaction_hash]
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==3

    # Replace generation 3's Ed25519 envelope with a syntactically valid HMAC envelope
    # over the same checkpoint payload. The ED25519_ONLY root must reject the downgrade.
    p=tmp_path/'chain'/'auth-00000000000000000003.json'
    record=json.loads(p.read_text()); payload=dict(record['envelope']['payload'])
    downgraded=HMACRecoveryAuthenticator('producer',H1,key_id='h1').sign(payload)
    record['envelope']={
        'version':downgraded.version,'producer_id':downgraded.producer_id,
        'algorithm':downgraded.algorithm,'key_id':downgraded.key_id,
        'payload_hash':downgraded.payload_hash,'payload':dict(downgraded.payload),
        'signature':downgraded.signature}
    p.write_text(json.dumps(record))
    failed=InfrastructureSupervisoryLoop([],config=cfg)
    assert failed._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==3
