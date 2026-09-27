import dataclasses, json
from durable_journal import DurableProofJournal
from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
from recovery_chain import AppendOnlyRecoveryChain
from recovery_lock import RecoveryChainLock
from test_proof_journal import fixture

def cfg(tmp_path,j): return LoopConfig(durable_proof_journal_path=str(j),startup_recovery_enabled=True,startup_recovery_now=20,recovery_chain_dir=str(tmp_path/'chain'),recovery_checkpoint_fsync=False,recovery_chain_lock_timeout_seconds=0.01)

def test_chain_startup_bootstrap_then_restore(tmp_path):
    j=tmp_path/'j'; tx=fixture(); DurableProofJournal(j).append(dataclasses.asdict(tx),fsync=False); c=cfg(tmp_path,j)
    first=InfrastructureSupervisoryLoop([],config=c); assert first._recovered_proof_transactions==()
    chain=AppendOnlyRecoveryChain(tmp_path/'chain'); assert chain.verify_chain().valid and chain.head().generation==1
    second=InfrastructureSupervisoryLoop([],config=c); assert [x.transaction_hash for x in second._recovered_proof_transactions]==[tx.transaction_hash]
    assert chain.verify_chain().valid and chain.head().generation==2

def test_stale_head_fails_closed_and_chain_not_advanced(tmp_path):
    j=tmp_path/'j'; DurableProofJournal(j).append(dataclasses.asdict(fixture()),fsync=False); c=cfg(tmp_path,j)
    InfrastructureSupervisoryLoop([],config=c); InfrastructureSupervisoryLoop([],config=c)
    chain=AppendOnlyRecoveryChain(tmp_path/'chain'); h1=chain._read_entry(1); chain.head_path.write_text(json.dumps({'generation':1,'chain_hash':h1.chain_hash}))
    before=len(list(chain.directory.glob('checkpoint-*.json'))); loop=InfrastructureSupervisoryLoop([],config=c)
    assert loop._recovered_proof_transactions==() and len(list(chain.directory.glob('checkpoint-*.json')))==before

def test_gap_or_tamper_fails_closed(tmp_path):
    j=tmp_path/'j'; DurableProofJournal(j).append(dataclasses.asdict(fixture()),fsync=False); c=cfg(tmp_path,j)
    InfrastructureSupervisoryLoop([],config=c); InfrastructureSupervisoryLoop([],config=c)
    chain=AppendOnlyRecoveryChain(tmp_path/'chain'); chain._entry_path(1).unlink(); loop=InfrastructureSupervisoryLoop([],config=c)
    assert loop._recovered_proof_transactions==()

def test_append_lock_contention_fails_closed_but_loop_constructs(tmp_path):
    j=tmp_path/'j'; DurableProofJournal(j).append(dataclasses.asdict(fixture()),fsync=False); c=cfg(tmp_path,j)
    lock=RecoveryChainLock(tmp_path/'chain/.append.lock',timeout_seconds=.01); assert lock.acquire()
    try: loop=InfrastructureSupervisoryLoop([],config=c); assert loop._recovered_proof_transactions==()
    finally: lock.release()

def test_lock_serializes(tmp_path):
    a=RecoveryChainLock(tmp_path/'x.lock',timeout_seconds=.01); b=RecoveryChainLock(tmp_path/'x.lock',timeout_seconds=.01)
    assert a.acquire() and not b.acquire(); a.release(); assert b.acquire(); b.release()

def test_chain_integration_has_no_new_mutation_authority(tmp_path):
    lock=RecoveryChainLock(tmp_path/'x')
    assert {'execute','mutate','promote','rollback'}.isdisjoint(dir(lock))
