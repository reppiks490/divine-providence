import dataclasses
from pathlib import Path
from durable_journal import DurableProofJournal
from recovery_policy import StartupRecoveryPolicy
from test_proof_journal import fixture
def mapping(tx): return dataclasses.asdict(tx)
def test_clean(tmp_path):
    j=DurableProofJournal(tmp_path/"p"); tx=fixture(); j.append(mapping(tx),fsync=False)
    d=StartupRecoveryPolicy(j.path).recover(now=20); assert d.proof_restore_eligible and len(d.accepted_transactions)==1 and d.decision_hash
def test_truncated_quarantine_fail_closed(tmp_path):
    j=DurableProofJournal(tmp_path/"p"); j.append(mapping(fixture()),fsync=False)
    with j.path.open("ab") as f:f.write(b"ISJ16")
    d=StartupRecoveryPolicy(j.path).recover(quarantine_dir=tmp_path/"q",now=20)
    assert d.original_tail_status=="truncated" and d.quarantined_bytes>0 and Path(d.quarantine_path).exists()
    assert j.recover().tail_status=="clean" and not d.proof_restore_eligible and not d.positive_learning_restore_eligible
def test_duplicate_blocks(tmp_path):
    j=DurableProofJournal(tmp_path/"p"); tx=fixture(); j.append(mapping(tx),fsync=False); j.append(mapping(tx),fsync=False)
    d=StartupRecoveryPolicy(j.path).recover(now=20); assert tx.intervention_id in d.duplicate_interventions and not d.proof_restore_eligible
def test_tampered_valid_frame_blocks(tmp_path):
    j=DurableProofJournal(tmp_path/"p"); bad=mapping(fixture()); bad["action_identity"]="forged"; j.append(bad,fsync=False)
    d=StartupRecoveryPolicy(j.path).recover(now=20); assert d.rejected_records==1 and not d.proof_restore_eligible
def test_empty_clean_gate_has_no_evidence(tmp_path):
    d=StartupRecoveryPolicy(tmp_path/"missing").recover(now=20); assert d.proof_restore_eligible and not d.accepted_transactions
def test_no_authority(tmp_path):
    assert {"execute","mutate","promote","rollback","acquire","release"}.isdisjoint(set(dir(StartupRecoveryPolicy(tmp_path/"p"))))
