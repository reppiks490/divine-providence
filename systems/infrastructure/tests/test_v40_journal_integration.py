import pytest
from recovery_asymmetric import Ed25519RecoverySigner, TrustRootKey
from recovery_governance_quorum import GovernanceApprovalSigner, GovernanceAuthorityQuorum
from recovery_governance_admission import AtomicGovernanceAdmissionStore
from recovery_witness_governance import WitnessGovernanceAuthority, WitnessGovernanceEpoch, WitnessGovernanceStore
from recovery_governance_transaction import CrashReconciledGovernanceStore
from recovery_governance_state_machine import JournalPhase

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

def test_successful_commit_reaches_committed_journal(tmp_path):
    tx,_,_,e,aps=setup(tmp_path); tx.commit(e,aps,fsync=False)
    assert tx.journal.current().phase == JournalPhase.COMMITTED
    assert tx.verify().valid

@pytest.mark.parametrize('point,phase',[('after_prepared',JournalPhase.PREPARED),('after_governance',JournalPhase.GOVERNANCE_WRITTEN),('after_admission',JournalPhase.ADMISSION_WRITTEN)])
def test_failpoint_recovery_is_idempotent(tmp_path,point,phase):
    tx,gs,adm,e,aps=setup(tmp_path)
    with pytest.raises(RuntimeError): tx.commit(e,aps,fsync=False,failpoint=point)
    assert tx.journal.current().phase == phase
    assert not tx.verify().valid
    tx.recover(fsync=False); tx.recover(fsync=False)
    assert tx.journal.current().phase == JournalPhase.COMMITTED
    assert tx.verify().valid and gs.verify_chain().valid and adm.verify_chain().valid

def test_partial_quorum_never_prepares_journal(tmp_path):
    tx,_,_,e,aps=setup(tmp_path)
    with pytest.raises(ValueError): tx.commit(e,aps[:1],fsync=False)
    assert tx.journal.current() is None

def test_journal_tamper_blocks_recovery(tmp_path):
    tx,_,_,e,aps=setup(tmp_path)
    with pytest.raises(RuntimeError): tx.commit(e,aps,fsync=False,failpoint='after_prepared')
    tx.journal.head.write_text('{"bad":true}')
    with pytest.raises(ValueError): tx.recover(fsync=False)
