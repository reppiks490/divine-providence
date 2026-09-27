import dataclasses
from durable_journal import DurableProofJournal
from recovery_policy import StartupRecoveryPolicy
from recovery_checkpoint import RecoveryCheckpoint
from recovery_continuity import RecoveryContinuityVerifier
from test_proof_journal import fixture

def recover(path): return StartupRecoveryPolicy(path).recover(now=20)
def test_continuity_accepts_same_history(tmp_path):
    p=tmp_path/'j'; DurableProofJournal(p).append(dataclasses.asdict(fixture()),fsync=False)
    d=recover(p); v=RecoveryContinuityVerifier().verify(RecoveryCheckpoint.from_decision(d),d)
    assert v.valid

def test_rollback_rejected(tmp_path):
    p=tmp_path/'j'; DurableProofJournal(p).append(dataclasses.asdict(fixture()),fsync=False)
    d=recover(p); cp=dataclasses.replace(RecoveryCheckpoint.from_decision(d), last_good_offset=d.last_good_offset+1)
    # re-hash not needed: invalid prior is itself rejected
    assert not RecoveryContinuityVerifier().verify(cp,d).valid

def test_journal_substitution_rejected(tmp_path):
    p=tmp_path/'j'; DurableProofJournal(p).append(dataclasses.asdict(fixture()),fsync=False)
    d=recover(p); cp=RecoveryCheckpoint.from_decision(d)
    other=dataclasses.replace(d,journal_path=str(tmp_path/'other'))
    assert not RecoveryContinuityVerifier().verify(cp,other).valid

def test_forked_proof_history_rejected(tmp_path):
    p=tmp_path/'j'; DurableProofJournal(p).append(dataclasses.asdict(fixture()),fsync=False)
    d=recover(p); cp=RecoveryCheckpoint.from_decision(d)
    fake=dataclasses.replace(d,accepted_transactions=(dataclasses.replace(d.accepted_transactions[0],transaction_hash='0'*64),))
    assert not RecoveryContinuityVerifier().verify(cp,fake).valid

def test_verifier_has_no_authority():
    assert {'execute','mutate','promote','rollback','acquire','release'}.isdisjoint(dir(RecoveryContinuityVerifier()))
from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
from recovery_checkpoint import AtomicRecoveryCheckpointStore

def test_startup_bootstraps_then_second_startup_restores(tmp_path):
    p=tmp_path/'j'; cp=tmp_path/'recovery.json'; DurableProofJournal(p).append(dataclasses.asdict(fixture()),fsync=False)
    cfg=LoopConfig(durable_proof_journal_path=str(p),startup_recovery_enabled=True,startup_recovery_now=20,recovery_checkpoint_path=str(cp),recovery_checkpoint_fsync=False)
    first=InfrastructureSupervisoryLoop([],config=cfg)
    assert first._recovered_proof_transactions == () and AtomicRecoveryCheckpointStore(cp).read() is not None
    second=InfrastructureSupervisoryLoop([],config=cfg)
    assert second._recovered_proof_transactions

def test_substituted_prior_checkpoint_blocks_restore_but_advances_current_checkpoint(tmp_path):
    p=tmp_path/'j'; cp=tmp_path/'recovery.json'; DurableProofJournal(p).append(dataclasses.asdict(fixture()),fsync=False)
    d=recover(p); bad=dataclasses.replace(RecoveryCheckpoint.from_decision(d),journal_path=str(tmp_path/'other'))
    # Rebuild a validly hashed checkpoint for the other journal using a substituted decision.
    otherd=dataclasses.replace(d,journal_path=str(tmp_path/'other'))
    AtomicRecoveryCheckpointStore(cp).write(RecoveryCheckpoint.from_decision(otherd),fsync=False)
    cfg=LoopConfig(durable_proof_journal_path=str(p),startup_recovery_enabled=True,startup_recovery_now=20,recovery_checkpoint_path=str(cp),recovery_checkpoint_fsync=False)
    loop=InfrastructureSupervisoryLoop([],config=cfg)
    assert loop._recovered_proof_transactions == ()
    assert AtomicRecoveryCheckpointStore(cp).read().journal_path == str(p)
