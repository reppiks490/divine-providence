import json, shutil
import pytest

from recovery_asymmetric import Ed25519RecoverySigner, RecoveryTrustRootManifest, TrustRootKey
from recovery_trust_root import (
    RecoveryAlgorithmMode, RecoveryTrustRootGeneration,
    RecoveryTrustRootAnchorAuthority, RecoveryTrustRootStore,
)
from recovery_witness import (
    TrustRootWitnessReceipt, TrustRootWitnessSigner, TrustRootWitnessVerifier,
    WitnessReceiptStore, WitnessQuorumVerifier, WitnessedTrustRootStore,
)

def manifest():
    producer=Ed25519RecoverySigner.generate("producer",key_id="p1")
    policy=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
    return RecoveryTrustRootManifest.issue(
        producer_id="producer",
        producer_keys=(TrustRootKey.from_verifier(producer.verifier(),purpose="recovery-producer"),),
        policy_authority=TrustRootKey.from_verifier(policy.verifier(),purpose="policy-authority"),
    )

def base_store(tmp_path):
    anchor=Ed25519RecoverySigner.generate("anchor",key_id="anchor")
    store=RecoveryTrustRootStore(tmp_path/"roots",RecoveryTrustRootAnchorAuthority(anchor))
    m=manifest()
    g1=RecoveryTrustRootGeneration.issue(
        generation=1,previous_generation_hash="0"*64,effective_recovery_generation=1,
        manifest=m,mode=RecoveryAlgorithmMode.ED25519_ONLY,
    )
    store.append(g1,fsync=False)
    return store,anchor,g1

def witnesses():
    signers=[TrustRootWitnessSigner(Ed25519RecoverySigner.generate(f"w{i}",key_id=f"w{i}")) for i in range(1,4)]
    verifiers={s.witness_id:s.verifier() for s in signers}
    return signers,verifiers

def test_quorum_accepts_two_of_three_matching_head(tmp_path):
    store,_,g1=base_store(tmp_path); signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    receipts.append(signers[0].attest(g1),fsync=False)
    receipts.append(signers[1].attest(g1),fsync=False)
    q=WitnessQuorumVerifier(verifiers,threshold=2)
    verdict=q.verify_head(store,receipts)
    assert verdict.valid and verdict.votes==2 and verdict.required==2

def test_partial_quorum_fails_closed(tmp_path):
    store,_,g1=base_store(tmp_path); signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    receipts.append(signers[0].attest(g1),fsync=False)
    verdict=WitnessQuorumVerifier(verifiers,threshold=2).verify_head(store,receipts)
    assert not verdict.valid and verdict.votes==1

def test_wrong_witness_signature_and_substitution_do_not_vote(tmp_path):
    store,_,g1=base_store(tmp_path); signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    r=signers[0].attest(g1)
    m=r.to_mapping(); m["witness_id"]="w2"
    receipts._path("w2",1).parent.mkdir(parents=True,exist_ok=True)
    receipts._path("w2",1).write_text(json.dumps(m))
    assert not WitnessQuorumVerifier(verifiers,threshold=1).verify_head(store,receipts).valid

def test_equivocation_same_witness_generation_is_rejected(tmp_path):
    store,_,g1=base_store(tmp_path); signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    receipts.append(signers[0].attest(g1),fsync=False)
    fake=TrustRootWitnessReceipt.issue_unsigned(
        witness_id=signers[0].witness_id,trust_root_generation=1,
        trust_root_generation_hash="f"*64,previous_receipt_hash="0"*64,
    )
    with pytest.raises(FileExistsError):
        receipts.append(signers[0].sign_receipt(fake),fsync=False)

def test_witness_history_detects_locally_consistent_root_rollback(tmp_path):
    store,anchor,g1=base_store(tmp_path); signers,verifiers=witnesses()
    m=manifest()
    g2=RecoveryTrustRootGeneration.issue(
        generation=2,previous_generation_hash=g1.generation_hash,effective_recovery_generation=2,
        manifest=m,mode=RecoveryAlgorithmMode.ED25519_ONLY,
    )
    store.append(g2,fsync=False)
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    for s in signers[:2]:
        receipts.append(s.attest(g1),fsync=False)
        receipts.append(s.attest(g2,previous_receipt=receipts.read(s.witness_id,1)),fsync=False)
    q=WitnessQuorumVerifier(verifiers,threshold=2)
    assert q.verify_head(store,receipts).valid
    # Attacker truncates local root history and rewrites local HEAD to a valid older state.
    (tmp_path/"roots"/"trust-root-00000000000000000002.json").unlink()
    (tmp_path/"roots"/"HEAD").write_text(json.dumps({"generation":1,"generation_hash":g1.generation_hash}))
    assert store.verify_chain().valid
    v=q.verify_head(store,receipts)
    assert not v.valid and "rollback" in v.reason

def test_witness_receipt_signature_tamper_rejected(tmp_path):
    store,_,g1=base_store(tmp_path); signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    receipts.append(signers[0].attest(g1),fsync=False)
    p=receipts._path(signers[0].witness_id,1)
    m=json.loads(p.read_text()); sig=m["signature"]; m["signature"]=("A" if sig[0]!="A" else "B")+sig[1:]; p.write_text(json.dumps(m))
    assert not WitnessQuorumVerifier(verifiers,threshold=1).verify_head(store,receipts).valid

def test_offline_public_verifiers_need_no_private_keys(tmp_path):
    store,_,g1=base_store(tmp_path); signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    for s in signers[:2]: receipts.append(s.attest(g1),fsync=False)
    q=WitnessQuorumVerifier(verifiers,threshold=2)
    assert q.verify_head(store,receipts).valid
    forbidden={"sign","attest","execute","mutate","promote","rollback","acquire","release"}
    for v in verifiers.values():
        assert forbidden.isdisjoint(dir(v))

def test_duplicate_witness_identity_cannot_inflate_quorum(tmp_path):
    store,_,g1=base_store(tmp_path); signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    receipts.append(signers[0].attest(g1),fsync=False)
    q=WitnessQuorumVerifier({signers[0].witness_id:verifiers[signers[0].witness_id]},threshold=2)
    assert not q.verify_head(store,receipts).valid

def test_witnessed_store_gates_root_access(tmp_path):
    store,_,g1=base_store(tmp_path); signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    wrapped=WitnessedTrustRootStore(store,receipts,WitnessQuorumVerifier(verifiers,threshold=2))
    assert wrapped.root_for_recovery_generation(1) is None
    for s in signers[:2]: receipts.append(s.attest(g1),fsync=False)
    assert wrapped.verify_chain().valid
    assert wrapped.root_for_recovery_generation(1).generation==1

def test_witness_components_have_no_infrastructure_authority(tmp_path):
    _,_,g1=base_store(tmp_path); signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    q=WitnessQuorumVerifier(verifiers,threshold=2)
    forbidden={"execute","mutate","promote","rollback","acquire","release"}
    for obj in [signers[0],verifiers["w1"],receipts,q]:
        assert forbidden.isdisjoint(dir(obj))

def test_witness_quorum_gates_actual_startup_restoration(tmp_path):
    import dataclasses
    from durable_journal import DurableProofJournal
    from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
    from recovery_auth import HMACRecoveryKeyring
    from recovery_asymmetric import Ed25519RecoveryKeyring
    from recovery_trust_root import MigrationAwareRecoveryAuthenticator
    from recovery_chain import AppendOnlyRecoveryChain
    from test_proof_journal import fixture

    # Root generation 1 is locally valid but runtime access is quorum-gated.
    anchor=Ed25519RecoverySigner.generate("anchor",key_id="anchor")
    producer=Ed25519RecoverySigner.generate("producer",key_id="ed1")
    policy=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
    m=RecoveryTrustRootManifest.issue(
        producer_id="producer",
        producer_keys=(TrustRootKey.from_verifier(producer.verifier(),purpose="recovery-producer"),),
        policy_authority=TrustRootKey.from_verifier(policy.verifier(),purpose="policy-authority"),
    )
    base=RecoveryTrustRootStore(tmp_path/"roots",RecoveryTrustRootAnchorAuthority(anchor))
    g1=RecoveryTrustRootGeneration.issue(
        generation=1,previous_generation_hash="0"*64,effective_recovery_generation=1,
        manifest=m,mode=RecoveryAlgorithmMode.HMAC_ONLY,
    )
    base.append(g1,fsync=False)

    signers,verifiers=witnesses()
    receipts=WitnessReceiptStore(tmp_path/"witnesses")
    receipts.append(signers[0].attest(g1),fsync=False)
    receipts.append(signers[1].attest(g1),fsync=False)
    witnessed=WitnessedTrustRootStore(base,receipts,WitnessQuorumVerifier(verifiers,threshold=2))

    auth=MigrationAwareRecoveryAuthenticator(
        HMACRecoveryKeyring("producer",{"h1":b"h"*32},signing_key_id="h1"),
        Ed25519RecoveryKeyring("producer",{"ed1":producer.verifier()},signer=producer),
        witnessed,
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

    # Corrupt one of the two quorum receipts: future startup must fail closed and not advance.
    wp=receipts._path(signers[1].witness_id,1)
    wm=json.loads(wp.read_text()); sig=wm["signature"]; wm["signature"]=("A" if sig[0]!="A" else "B")+sig[1:]
    wp.write_text(json.dumps(wm))
    failed=InfrastructureSupervisoryLoop([],config=cfg)
    assert failed._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/"chain").verify_chain().generation==2
