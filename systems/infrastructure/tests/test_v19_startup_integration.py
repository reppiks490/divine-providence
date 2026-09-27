import dataclasses
from durable_journal import DurableProofJournal
from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
from test_proof_journal import fixture

def mapping(tx): return dataclasses.asdict(tx)

def test_startup_recovery_opt_in_restores_clean_verified_proof(tmp_path):
    path=tmp_path/'proof.journal'; tx=fixture(); DurableProofJournal(path).append(mapping(tx),fsync=False)
    loop=InfrastructureSupervisoryLoop([],config=LoopConfig(durable_proof_journal_path=str(path),startup_recovery_enabled=True, startup_recovery_now=20))
    assert loop._startup_recovery_decision is not None
    assert loop._startup_recovery_decision.proof_restore_eligible
    assert [x.transaction_hash for x in loop._recovered_proof_transactions]==[tx.transaction_hash]

def test_startup_recovery_damaged_tail_quarantines_and_restores_nothing(tmp_path):
    path=tmp_path/'proof.journal'; tx=fixture(); DurableProofJournal(path).append(mapping(tx),fsync=False)
    with path.open('ab') as f: f.write(b'ISJ16')
    loop=InfrastructureSupervisoryLoop([],config=LoopConfig(durable_proof_journal_path=str(path),startup_recovery_enabled=True,recovery_quarantine_dir=str(tmp_path/'q')))
    assert loop._startup_recovery_decision.original_tail_status=='truncated'
    assert not loop._startup_recovery_decision.proof_restore_eligible
    assert loop._recovered_proof_transactions==()

def test_startup_recovery_disabled_preserves_prior_behavior(tmp_path):
    path=tmp_path/'proof.journal'; DurableProofJournal(path).append(mapping(fixture()),fsync=False)
    loop=InfrastructureSupervisoryLoop([],config=LoopConfig(durable_proof_journal_path=str(path)))
    assert loop._startup_recovery_decision is None and loop._recovered_proof_transactions==()

def test_startup_recovery_internal_failure_fails_open_for_loop(monkeypatch,tmp_path):
    def boom(*a,**k): raise OSError('simulated recovery failure')
    monkeypatch.setattr('infrastructure_loop.StartupRecoveryPolicy.recover',boom)
    loop=InfrastructureSupervisoryLoop([],config=LoopConfig(durable_proof_journal_path=str(tmp_path/'p'),startup_recovery_enabled=True))
    assert loop._startup_recovery_decision is None and loop._recovered_proof_transactions==()

def test_v20_startup_persists_independently_verifiable_checkpoint(tmp_path):
    from recovery_checkpoint import AtomicRecoveryCheckpointStore
    path=tmp_path/'proof.journal'; tx=fixture(); DurableProofJournal(path).append(mapping(tx),fsync=False)
    cp=tmp_path/'recovery.json'
    loop=InfrastructureSupervisoryLoop([],config=LoopConfig(durable_proof_journal_path=str(path),startup_recovery_enabled=True,startup_recovery_now=20,recovery_checkpoint_path=str(cp),recovery_checkpoint_fsync=False))
    got=AtomicRecoveryCheckpointStore(cp).read()
    assert got is not None and got.verify(loop._startup_recovery_decision)

def test_v20_checkpoint_write_failure_does_not_block_supervision(monkeypatch,tmp_path):
    def boom(*a,**k): raise OSError('simulated checkpoint failure')
    monkeypatch.setattr('infrastructure_loop.AtomicRecoveryCheckpointStore.write',boom)
    path=tmp_path/'proof.journal'; DurableProofJournal(path).append(mapping(fixture()),fsync=False)
    loop=InfrastructureSupervisoryLoop([],config=LoopConfig(durable_proof_journal_path=str(path),startup_recovery_enabled=True,startup_recovery_now=20,recovery_checkpoint_path=str(tmp_path/'r')))
    assert loop._startup_recovery_decision.proof_restore_eligible
    assert loop._recovered_proof_transactions == ()  # V21: checkpoint failure cannot restore trust
