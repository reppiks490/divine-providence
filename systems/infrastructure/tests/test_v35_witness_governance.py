import json
import pytest

from recovery_asymmetric import Ed25519RecoverySigner, RecoveryTrustRootManifest, TrustRootKey
from recovery_trust_root import (
    RecoveryAlgorithmMode, RecoveryTrustRootGeneration,
    RecoveryTrustRootAnchorAuthority, RecoveryTrustRootStore,
)
from recovery_witness import TrustRootWitnessSigner, WitnessReceiptStore
from recovery_witness_governance import (
    WitnessGovernanceEpoch, WitnessGovernanceAuthority, WitnessGovernanceStore,
    GovernedWitnessedTrustRootStore, TransparencyCheckpoint, TransparencyCheckpointStore,
    compare_transparency_gossip,
)

def manifest():
    producer=Ed25519RecoverySigner.generate("producer",key_id="p1")
    policy=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
    return RecoveryTrustRootManifest.issue(
        producer_id="producer",
        producer_keys=(TrustRootKey.from_verifier(producer.verifier(),purpose="recovery-producer"),),
        policy_authority=TrustRootKey.from_verifier(policy.verifier(),purpose="policy-authority"),
    )

def root_store(tmp_path):
    anchor=Ed25519RecoverySigner.generate("anchor",key_id="anchor")
    store=RecoveryTrustRootStore(tmp_path/"roots",RecoveryTrustRootAnchorAuthority(anchor))
    m=manifest()
    g1=RecoveryTrustRootGeneration.issue(
        generation=1,previous_generation_hash="0"*64,effective_recovery_generation=1,
        manifest=m,mode=RecoveryAlgorithmMode.ED25519_ONLY,
    )
    store.append(g1,fsync=False)
    return store,g1

def witness_signers(n=4):
    return [TrustRootWitnessSigner(Ed25519RecoverySigner.generate(f"w{i}",key_id=f"w{i}")) for i in range(1,n+1)]

def witness_key(s):
    return TrustRootKey.from_verifier(s.verifier()._verifier,purpose="trust-root-witness")

def governance(tmp_path, signers, threshold=2):
    authority_signer=Ed25519RecoverySigner.generate("witness-governance",key_id="gov")
    authority=WitnessGovernanceAuthority(authority_signer)
    store=WitnessGovernanceStore(tmp_path/"governance",authority)
    e1=WitnessGovernanceEpoch.issue(
        epoch=1,previous_epoch_hash="0"*64,effective_trust_root_generation=1,
        threshold=threshold,witness_keys=tuple(witness_key(s) for s in signers),
    )
    store.append(e1,fsync=False)
    return store,authority_signer,e1

def test_signed_witness_governance_genesis_and_public_only_verify(tmp_path):
    signers=witness_signers(3)
    store,authority_signer,e1=governance(tmp_path,signers,threshold=2)
    assert store.verify_chain().valid
    public=WitnessGovernanceStore(
        tmp_path/"governance",
        WitnessGovernanceAuthority(verifier=authority_signer.verifier())
    )
    assert public.verify_chain().valid
    assert public.epoch_for_trust_root_generation(1).epoch==1

def test_threshold_reduction_is_rejected(tmp_path):
    signers=witness_signers(4)
    store,_,e1=governance(tmp_path,signers,threshold=3)
    e2=WitnessGovernanceEpoch.issue(
        epoch=2,previous_epoch_hash=e1.epoch_hash,effective_trust_root_generation=2,
        threshold=2,witness_keys=tuple(witness_key(s) for s in signers),
    )
    with pytest.raises(ValueError):
        store.append(e2,fsync=False)

def test_full_witness_set_substitution_without_quorum_overlap_rejected(tmp_path):
    old=witness_signers(3); new=[TrustRootWitnessSigner(Ed25519RecoverySigner.generate(f"n{i}",key_id=f"n{i}")) for i in range(1,4)]
    store,_,e1=governance(tmp_path,old,threshold=2)
    e2=WitnessGovernanceEpoch.issue(
        epoch=2,previous_epoch_hash=e1.epoch_hash,effective_trust_root_generation=2,
        threshold=2,witness_keys=tuple(witness_key(s) for s in new),
    )
    with pytest.raises(ValueError):
        store.append(e2,fsync=False)

def test_gradual_rotation_with_quorum_overlap_is_allowed(tmp_path):
    old=witness_signers(3)
    extra=TrustRootWitnessSigner(Ed25519RecoverySigner.generate("w4",key_id="w4"))
    store,_,e1=governance(tmp_path,old,threshold=2)
    e2=WitnessGovernanceEpoch.issue(
        epoch=2,previous_epoch_hash=e1.epoch_hash,effective_trust_root_generation=2,
        threshold=2,witness_keys=(witness_key(old[0]),witness_key(old[1]),witness_key(extra)),
    )
    store.append(e2,fsync=False)
    assert store.verify_chain().valid

def test_governance_head_replay_rejected(tmp_path):
    signers=witness_signers(3)
    store,_,e1=governance(tmp_path,signers,threshold=2)
    old_head=(tmp_path/"governance"/"HEAD").read_text()
    e2=WitnessGovernanceEpoch.issue(
        epoch=2,previous_epoch_hash=e1.epoch_hash,effective_trust_root_generation=2,
        threshold=2,witness_keys=tuple(witness_key(s) for s in signers),
    )
    store.append(e2,fsync=False)
    (tmp_path/"governance"/"HEAD").write_text(old_head)
    assert not store.verify_chain().valid

def test_governed_witnessed_store_uses_applicable_membership_and_threshold(tmp_path):
    roots,g1=root_store(tmp_path)
    signers=witness_signers(3)
    gov,_,_=governance(tmp_path,signers,threshold=2)
    receipts=WitnessReceiptStore(tmp_path/"receipts")
    receipts.append(signers[0].attest(g1),fsync=False)
    wrapped=GovernedWitnessedTrustRootStore(roots,receipts,gov)
    assert not wrapped.verify_chain().valid
    receipts.append(signers[1].attest(g1),fsync=False)
    assert wrapped.verify_chain().valid
    assert wrapped.root_for_recovery_generation(1).generation==1

def test_transparency_checkpoint_is_signed_hash_linked_and_exportable(tmp_path):
    roots,g1=root_store(tmp_path)
    signers=witness_signers(3)
    gov,authority_signer,e1=governance(tmp_path,signers,threshold=2)
    receipts=WitnessReceiptStore(tmp_path/"receipts")
    r1=signers[0].attest(g1); r2=signers[1].attest(g1)
    receipts.append(r1,fsync=False); receipts.append(r2,fsync=False)
    tstore=TransparencyCheckpointStore(
        tmp_path/"transparency",
        WitnessGovernanceAuthority(authority_signer)
    )
    cp=TransparencyCheckpoint.issue(
        sequence=1,previous_checkpoint_hash="0"*64,
        trust_root_generation=1,trust_root_generation_hash=g1.generation_hash,
        governance_epoch=1,governance_epoch_hash=e1.epoch_hash,
        witness_receipt_hashes=(r1.receipt_hash,r2.receipt_hash),
    )
    tstore.append(cp,fsync=False)
    assert tstore.verify_chain().valid
    exported=tstore.export_digest()
    assert exported["sequence"]==1 and exported["checkpoint_hash"]==cp.checkpoint_hash
    verify_only=TransparencyCheckpointStore(
        tmp_path/"transparency",
        WitnessGovernanceAuthority(verifier=authority_signer.verifier())
    )
    assert verify_only.verify_chain().valid

def test_transparency_head_replay_rejected(tmp_path):
    roots,g1=root_store(tmp_path); signers=witness_signers(3)
    gov,authority_signer,e1=governance(tmp_path,signers,threshold=2)
    t=TransparencyCheckpointStore(tmp_path/"transparency",WitnessGovernanceAuthority(authority_signer))
    c1=TransparencyCheckpoint.issue(
        sequence=1,previous_checkpoint_hash="0"*64,trust_root_generation=1,
        trust_root_generation_hash=g1.generation_hash,governance_epoch=1,
        governance_epoch_hash=e1.epoch_hash,witness_receipt_hashes=("a"*64,"b"*64),
    )
    t.append(c1,fsync=False); old_head=(tmp_path/"transparency"/"HEAD").read_text()
    c2=TransparencyCheckpoint.issue(
        sequence=2,previous_checkpoint_hash=c1.checkpoint_hash,trust_root_generation=1,
        trust_root_generation_hash=g1.generation_hash,governance_epoch=1,
        governance_epoch_hash=e1.epoch_hash,witness_receipt_hashes=("c"*64,"d"*64),
    )
    t.append(c2,fsync=False)
    (tmp_path/"transparency"/"HEAD").write_text(old_head)
    assert not t.verify_chain().valid

def test_gossip_detects_same_sequence_split_view():
    a={"sequence":7,"checkpoint_hash":"a"*64}
    b={"sequence":7,"checkpoint_hash":"b"*64}
    v=compare_transparency_gossip(a,b)
    assert not v.valid and v.equivocation

def test_gossip_reports_stale_peer_without_calling_it_equivocation():
    a={"sequence":8,"checkpoint_hash":"a"*64}
    b={"sequence":7,"checkpoint_hash":"b"*64}
    v=compare_transparency_gossip(a,b)
    assert not v.valid and not v.equivocation and v.stale

def test_governance_and_transparency_components_have_no_infrastructure_authority(tmp_path):
    signers=witness_signers(3)
    store,authority_signer,_=governance(tmp_path,signers,threshold=2)
    t=TransparencyCheckpointStore(tmp_path/"transparency",WitnessGovernanceAuthority(authority_signer))
    forbidden={"execute","mutate","promote","rollback","acquire","release"}
    for obj in [store,t,WitnessGovernanceAuthority(verifier=authority_signer.verifier())]:
        assert forbidden.isdisjoint(dir(obj))

def test_duplicate_witness_subject_with_different_keys_is_rejected():
    a=TrustRootWitnessSigner(Ed25519RecoverySigner.generate("same",key_id="a"))
    b=TrustRootWitnessSigner(Ed25519RecoverySigner.generate("same",key_id="b"))
    with pytest.raises(ValueError):
        WitnessGovernanceEpoch.issue(
            epoch=1,previous_epoch_hash="0"*64,effective_trust_root_generation=1,
            threshold=1,witness_keys=(witness_key(a),witness_key(b)),
        )

def test_verified_transparency_checkpoint_is_derived_from_current_governed_quorum(tmp_path):
    roots,g1=root_store(tmp_path)
    signers=witness_signers(3)
    gov,authority_signer,e1=governance(tmp_path,signers,threshold=2)
    receipts=WitnessReceiptStore(tmp_path/"receipts")
    r1=signers[0].attest(g1); r2=signers[1].attest(g1)
    receipts.append(r1,fsync=False); receipts.append(r2,fsync=False)
    t=TransparencyCheckpointStore(tmp_path/"transparency",WitnessGovernanceAuthority(authority_signer))
    signed=t.append_current(roots,gov,receipts,fsync=False)
    cp=signed.checkpoint
    assert cp.trust_root_generation==1
    assert cp.trust_root_generation_hash==g1.generation_hash
    assert cp.governance_epoch==1 and cp.governance_epoch_hash==e1.epoch_hash
    assert set(cp.witness_receipt_hashes)=={r1.receipt_hash,r2.receipt_hash}

def test_verified_transparency_checkpoint_refuses_partial_quorum(tmp_path):
    roots,g1=root_store(tmp_path)
    signers=witness_signers(3)
    gov,authority_signer,_=governance(tmp_path,signers,threshold=2)
    receipts=WitnessReceiptStore(tmp_path/"receipts")
    receipts.append(signers[0].attest(g1),fsync=False)
    t=TransparencyCheckpointStore(tmp_path/"transparency",WitnessGovernanceAuthority(authority_signer))
    with pytest.raises(ValueError):
        t.append_current(roots,gov,receipts,fsync=False)

def test_governed_witness_set_gates_actual_startup_restoration(tmp_path):
    import dataclasses
    from durable_journal import DurableProofJournal
    from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
    from recovery_auth import HMACRecoveryKeyring
    from recovery_asymmetric import Ed25519RecoveryKeyring
    from recovery_trust_root import MigrationAwareRecoveryAuthenticator
    from recovery_chain import AppendOnlyRecoveryChain
    from test_proof_journal import fixture

    anchor=Ed25519RecoverySigner.generate("anchor",key_id="anchor")
    producer=Ed25519RecoverySigner.generate("producer",key_id="ed1")
    policy=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
    m=RecoveryTrustRootManifest.issue(
        producer_id="producer",
        producer_keys=(TrustRootKey.from_verifier(producer.verifier(),purpose="recovery-producer"),),
        policy_authority=TrustRootKey.from_verifier(policy.verifier(),purpose="policy-authority"),
    )
    roots=RecoveryTrustRootStore(tmp_path/"roots",RecoveryTrustRootAnchorAuthority(anchor))
    g1=RecoveryTrustRootGeneration.issue(
        generation=1,previous_generation_hash="0"*64,effective_recovery_generation=1,
        manifest=m,mode=RecoveryAlgorithmMode.HMAC_ONLY,
    )
    roots.append(g1,fsync=False)

    signers=witness_signers(3)
    gov,_,_=governance(tmp_path,signers,threshold=2)
    receipts=WitnessReceiptStore(tmp_path/"receipts")
    receipts.append(signers[0].attest(g1),fsync=False)
    receipts.append(signers[1].attest(g1),fsync=False)
    governed=GovernedWitnessedTrustRootStore(roots,receipts,gov)

    auth=__import__("recovery_trust_root").MigrationAwareRecoveryAuthenticator(
        HMACRecoveryKeyring("producer",{"h1":b"h"*32},signing_key_id="h1"),
        Ed25519RecoveryKeyring("producer",{"ed1":producer.verifier()},signer=producer),
        governed,
    )
    journal=tmp_path/"proof.journal"; tx=fixture()
    DurableProofJournal(journal).append(dataclasses.asdict(tx),fsync=False)
    cfg=LoopConfig(
        durable_proof_journal_path=str(journal),startup_recovery_enabled=True,startup_recovery_now=20,
        recovery_chain_dir=str(tmp_path/"chain"),recovery_checkpoint_fsync=False,
        recovery_chain_lock_timeout_seconds=.01,recovery_authenticator=auth,
    )

    first=InfrastructureSupervisoryLoop([],config=cfg)
    assert first._recovered_proof_transactions==()
    second=InfrastructureSupervisoryLoop([],config=cfg)
    assert [x.transaction_hash for x in second._recovered_proof_transactions]==[tx.transaction_hash]
    assert AppendOnlyRecoveryChain(tmp_path/"chain").verify_chain().generation==2

    # Governance rollback invalidates witness trust even though the witness receipts remain intact.
    hp=tmp_path/"governance"/"HEAD"
    hm=json.loads(hp.read_text()); hm["epoch_hash"]="0"*64; hp.write_text(json.dumps(hm))
    failed=InfrastructureSupervisoryLoop([],config=cfg)
    assert failed._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/"chain").verify_chain().generation==2
