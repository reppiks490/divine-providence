import dataclasses, json
from durable_journal import DurableProofJournal
from recovery_policy import StartupRecoveryPolicy
from recovery_checkpoint import RecoveryCheckpoint, AtomicRecoveryCheckpointStore
from test_proof_journal import fixture

def decision(tmp_path):
    p=tmp_path/'proof.journal'; DurableProofJournal(p).append(dataclasses.asdict(fixture()),fsync=False)
    return StartupRecoveryPolicy(p).recover(now=20)

def test_checkpoint_roundtrip_and_decision_binding(tmp_path):
    d=decision(tmp_path); cp=RecoveryCheckpoint.from_decision(d); s=AtomicRecoveryCheckpointStore(tmp_path/'recovery.json')
    s.write(cp,fsync=False); got=s.read(); assert got==cp and got.verify(d)

def test_tampered_checkpoint_rejected(tmp_path):
    d=decision(tmp_path); cp=RecoveryCheckpoint.from_decision(d); s=AtomicRecoveryCheckpointStore(tmp_path/'recovery.json'); s.write(cp,fsync=False)
    x=json.loads(s.path.read_text()); x['last_good_offset']+=1; s.path.write_text(json.dumps(x))
    assert s.read() is None

def test_checkpoint_from_other_decision_rejected(tmp_path):
    d=decision(tmp_path); cp=RecoveryCheckpoint.from_decision(d)
    other=dataclasses.replace(d, decision_hash='0'*64)
    assert cp.verify() and not cp.verify(other)

def test_truncated_checkpoint_rejected(tmp_path):
    s=AtomicRecoveryCheckpointStore(tmp_path/'recovery.json'); s.path.write_bytes(b'{"schema":')
    assert s.read() is None

def test_store_has_no_mutation_authority(tmp_path):
    s=AtomicRecoveryCheckpointStore(tmp_path/'r')
    assert {'execute','mutate','promote','rollback','acquire','release'}.isdisjoint(dir(s))
