import pytest
from recovery_governance_state_machine import JournalPhase, GovernanceTransactionJournal

def test_phase_order_and_terminal_commit(tmp_path):
    j=GovernanceTransactionJournal(tmp_path)
    r=j.prepare(1,'a'*64,fsync=False); assert r.phase==JournalPhase.PREPARED
    assert j.advance(1,JournalPhase.GOVERNANCE_WRITTEN,fsync=False).phase==JournalPhase.GOVERNANCE_WRITTEN
    assert j.advance(1,JournalPhase.ADMISSION_WRITTEN,fsync=False).phase==JournalPhase.ADMISSION_WRITTEN
    assert j.advance(1,JournalPhase.COMMITTED,fsync=False).phase==JournalPhase.COMMITTED
    assert j.verify().valid

def test_phase_skip_and_regression_rejected(tmp_path):
    j=GovernanceTransactionJournal(tmp_path); j.prepare(1,'a'*64,fsync=False)
    with pytest.raises(ValueError): j.advance(1,JournalPhase.ADMISSION_WRITTEN,fsync=False)
    j.advance(1,JournalPhase.GOVERNANCE_WRITTEN,fsync=False)
    with pytest.raises(ValueError): j.advance(1,JournalPhase.PREPARED,fsync=False)

def test_stale_head_rejected(tmp_path):
    j=GovernanceTransactionJournal(tmp_path); j.prepare(1,'a'*64,fsync=False); j.advance(1,JournalPhase.GOVERNANCE_WRITTEN,fsync=False)
    (tmp_path/'HEAD').write_text('{"epoch":1,"phase":"PREPARED","record_hash":"'+'0'*64+'"}')
    assert not j.verify().valid

def test_reopen_is_deterministic(tmp_path):
    j=GovernanceTransactionJournal(tmp_path); j.prepare(1,'a'*64,fsync=False); j.advance(1,JournalPhase.GOVERNANCE_WRITTEN,fsync=False)
    j2=GovernanceTransactionJournal(tmp_path); assert j2.verify().valid and j2.current().phase==JournalPhase.GOVERNANCE_WRITTEN

def test_no_mutation_authority(tmp_path):
    j=GovernanceTransactionJournal(tmp_path)
    assert {'execute','mutate','promote','rollback','acquire','release'}.isdisjoint(dir(j))
