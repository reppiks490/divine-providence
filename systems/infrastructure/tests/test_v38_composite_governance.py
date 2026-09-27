import json, pytest
from recovery_asymmetric import Ed25519RecoverySigner, TrustRootKey
from recovery_governance_quorum import GovernanceApprovalSigner, GovernanceAuthorityQuorum
from recovery_governance_admission import AtomicGovernanceAdmissionStore
from recovery_witness_governance import WitnessGovernanceAuthority, WitnessGovernanceEpoch, WitnessGovernanceStore
from recovery_governance_transaction import CrashReconciledGovernanceStore

def signers(p,n): return [Ed25519RecoverySigner.generate(f'{p}{i}',key_id=f'{p}{i}') for i in range(n)]
def wk(s): return TrustRootKey.from_verifier(s.verifier(),purpose='trust-root-witness')
def setup(tmp_path):
    ws=signers('w',3); gas=signers('ga',3); root=Ed25519RecoverySigner.generate('gov-root',key_id='root')
    gs=WitnessGovernanceStore(tmp_path/'gov',WitnessGovernanceAuthority(root))
    adm=AtomicGovernanceAdmissionStore(tmp_path/'adm',GovernanceAuthorityQuorum([x.verifier() for x in gas],2))
    tx=CrashReconciledGovernanceStore(gs,adm,tmp_path/'tx')
    e=WitnessGovernanceEpoch.issue(epoch=1,previous_epoch_hash='0'*64,effective_trust_root_generation=1,threshold=2,witness_keys=tuple(wk(x) for x in ws))
    aps=[GovernanceApprovalSigner(x).approve(1,e.epoch_hash) for x in gas[:2]]
    return tx,gs,adm,e,aps

def test_commit_binds_governance_and_admission(tmp_path):
    tx,gs,adm,e,aps=setup(tmp_path); tx.commit(e,aps,fsync=False)
    assert gs.verify_chain().valid and adm.verify_chain().valid and tx.verify().valid

def test_partial_quorum_writes_nothing(tmp_path):
    tx,gs,adm,e,aps=setup(tmp_path)
    with pytest.raises(ValueError): tx.commit(e,aps[:1],fsync=False)
    assert gs.verify_chain(allow_empty=True).valid and adm.verify_chain(allow_empty=True).valid

def test_crash_after_governance_record_reconciles_idempotently(tmp_path):
    tx,gs,adm,e,aps=setup(tmp_path)
    with pytest.raises(RuntimeError): tx.commit(e,aps,fsync=False,failpoint='after_governance')
    tx.recover(fsync=False); tx.recover(fsync=False)
    assert tx.verify().valid and gs.verify_chain().valid and adm.verify_chain().valid

def test_crash_after_admission_reconciles_idempotently(tmp_path):
    tx,gs,adm,e,aps=setup(tmp_path)
    with pytest.raises(RuntimeError): tx.commit(e,aps,fsync=False,failpoint='after_admission')
    tx.recover(fsync=False); tx.recover(fsync=False)
    assert tx.verify().valid

def test_stale_head_fails_closed(tmp_path):
    tx,gs,adm,e,aps=setup(tmp_path); tx.commit(e,aps,fsync=False)
    gs.head_path.write_text(json.dumps({'epoch':0,'epoch_hash':'0'*64}))
    assert not tx.verify().valid

def test_duplicate_replay_rejected(tmp_path):
    tx,gs,adm,e,aps=setup(tmp_path); tx.commit(e,aps,fsync=False)
    with pytest.raises((ValueError,FileExistsError)): tx.commit(e,aps,fsync=False)

def test_no_mutation_authority(tmp_path):
    tx,*_=setup(tmp_path); assert {'execute','mutate','promote','rollback','acquire','release'}.isdisjoint(dir(tx))
from recovery_governance_quorum import TransparencyAnchorSigner, TransparencyAnchorQuorum, FreshnessPolicy
from recovery_transparency_import import AnchoredCheckpointImporter

def test_import_requires_anchor_quorum_and_freshness(tmp_path):
    logs=signers('log',3); q=TransparencyAnchorQuorum([x.verifier() for x in logs],2)
    imp=AnchoredCheckpointImporter(tmp_path/'remote.json',q,FreshnessPolicy(60,5))
    d={'sequence':5,'checkpoint_hash':'c'*64,'observed_at':1000}
    rs=[TransparencyAnchorSigner(x).anchor(5,'c'*64,1000) for x in logs[:2]]
    assert imp.admit(d,rs,now=1050).valid

def test_import_partial_quorum_stale_and_rollback_fail_closed(tmp_path):
    logs=signers('log',3); q=TransparencyAnchorQuorum([x.verifier() for x in logs],2)
    imp=AnchoredCheckpointImporter(tmp_path/'remote.json',q,FreshnessPolicy(60,5)); d={'sequence':5,'checkpoint_hash':'c'*64,'observed_at':1000}
    with pytest.raises(ValueError): imp.admit(d,[TransparencyAnchorSigner(logs[0]).anchor(5,'c'*64,1000)],now=1050)
    rs=[TransparencyAnchorSigner(x).anchor(5,'c'*64,1000) for x in logs[:2]]; imp.admit(d,rs,now=1050)
    old={'sequence':4,'checkpoint_hash':'d'*64,'observed_at':1050}; ors=[TransparencyAnchorSigner(x).anchor(4,'d'*64,1050) for x in logs[:2]]
    with pytest.raises(ValueError): imp.admit(old,ors,now=1050)
    stale={'sequence':6,'checkpoint_hash':'e'*64,'observed_at':900}; srs=[TransparencyAnchorSigner(x).anchor(6,'e'*64,900) for x in logs[:2]]
    with pytest.raises(ValueError): imp.admit(stale,srs,now=1050)
