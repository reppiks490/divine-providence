import dataclasses, json
from durable_journal import DurableProofJournal
from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
from recovery_auth import HMACRecoveryAuthenticator, HMACRecoveryKeyring, AuthenticatedRecoveryEnvelope
from recovery_chain import AppendOnlyRecoveryChain, AuthenticatedRecoveryChain
from test_proof_journal import fixture


def cfg(tmp_path, journal, authenticator):
    return LoopConfig(
        durable_proof_journal_path=str(journal),
        startup_recovery_enabled=True,
        startup_recovery_now=20,
        recovery_chain_dir=str(tmp_path / 'chain'),
        recovery_checkpoint_fsync=False,
        recovery_chain_lock_timeout_seconds=0.01,
        recovery_authenticator=authenticator,
    )


def seed(tmp_path):
    journal=tmp_path/'proof.journal'; tx=fixture()
    DurableProofJournal(journal).append(dataclasses.asdict(tx),fsync=False)
    return journal,tx


def test_authenticated_startup_bootstrap_then_restore(tmp_path):
    journal,tx=seed(tmp_path); auth=HMACRecoveryAuthenticator('producer',b'k'*32,key_id='k1'); c=cfg(tmp_path,journal,auth)
    first=InfrastructureSupervisoryLoop([],config=c)
    assert first._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==1
    assert AuthenticatedRecoveryChain(tmp_path/'chain',auth).verify_chain().generation==1
    second=InfrastructureSupervisoryLoop([],config=c)
    assert [x.transaction_hash for x in second._recovered_proof_transactions]==[tx.transaction_hash]
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==2
    assert AuthenticatedRecoveryChain(tmp_path/'chain',auth).verify_chain().generation==2


def test_unsigned_downgrade_at_startup_fails_closed_without_advancing(tmp_path):
    journal,_=seed(tmp_path); auth=HMACRecoveryAuthenticator('producer',b'k'*32,key_id='k1'); c=cfg(tmp_path,journal,auth)
    InfrastructureSupervisoryLoop([],config=c)
    (tmp_path/'chain'/'auth-00000000000000000001.json').unlink()
    loop=InfrastructureSupervisoryLoop([],config=c)
    assert loop._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==1


def test_wrong_key_at_startup_fails_closed_without_advancing(tmp_path):
    journal,_=seed(tmp_path); first_auth=HMACRecoveryAuthenticator('producer',b'a'*32,key_id='k1')
    InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,first_auth))
    wrong=HMACRecoveryAuthenticator('producer',b'b'*32,key_id='k1')
    loop=InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,wrong))
    assert loop._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==1


def test_signature_tamper_at_startup_fails_closed(tmp_path):
    journal,_=seed(tmp_path); auth=HMACRecoveryAuthenticator('producer',b'a'*32,key_id='k1'); c=cfg(tmp_path,journal,auth)
    InfrastructureSupervisoryLoop([],config=c)
    p=tmp_path/'chain'/'auth-00000000000000000001.json'; m=json.loads(p.read_text()); m['envelope']['signature']='0'*64; p.write_text(json.dumps(m))
    loop=InfrastructureSupervisoryLoop([],config=c)
    assert loop._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==1



def test_wrong_producer_at_startup_fails_closed(tmp_path):
    journal,_=seed(tmp_path); first=HMACRecoveryAuthenticator('producer-A',b'a'*32,key_id='k1')
    InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,first))
    wrong=HMACRecoveryAuthenticator('producer-B',b'a'*32,key_id='k1')
    loop=InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,wrong))
    assert loop._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==1


def test_version_tamper_at_startup_fails_closed(tmp_path):
    journal,_=seed(tmp_path); auth=HMACRecoveryAuthenticator('producer',b'a'*32,key_id='k1'); c=cfg(tmp_path,journal,auth)
    InfrastructureSupervisoryLoop([],config=c)
    p=tmp_path/'chain'/'auth-00000000000000000001.json'; m=json.loads(p.read_text()); m['envelope']['version']+=1; p.write_text(json.dumps(m))
    loop=InfrastructureSupervisoryLoop([],config=c)
    assert loop._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==1

def test_rotation_keyring_verifies_old_and_signs_new(tmp_path):
    journal,tx=seed(tmp_path)
    old=HMACRecoveryAuthenticator('producer',b'o'*32,key_id='old')
    InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,old))
    ring=HMACRecoveryKeyring('producer',{'old':b'o'*32,'new':b'n'*32},signing_key_id='new')
    second=InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,ring))
    assert [x.transaction_hash for x in second._recovered_proof_transactions]==[tx.transaction_hash]
    m=json.loads((tmp_path/'chain'/'auth-00000000000000000002.json').read_text())
    assert m['envelope']['key_id']=='new'
    third=InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,ring))
    assert [x.transaction_hash for x in third._recovered_proof_transactions]==[tx.transaction_hash]


def test_algorithm_version_and_key_id_mismatch_rejected():
    ring=HMACRecoveryKeyring('producer',{'k1':b'k'*32},signing_key_id='k1'); e=ring.sign({'x':1})
    assert not ring.verify(AuthenticatedRecoveryEnvelope(e.version+1,e.producer_id,e.algorithm,e.payload_hash,e.payload,e.signature,e.key_id))
    assert not ring.verify(AuthenticatedRecoveryEnvelope(e.version,e.producer_id,'OTHER',e.payload_hash,e.payload,e.signature,e.key_id))
    assert not ring.verify(AuthenticatedRecoveryEnvelope(e.version,e.producer_id,e.algorithm,e.payload_hash,e.payload,e.signature,'missing'))


def test_keyring_has_no_mutation_authority():
    ring=HMACRecoveryKeyring('producer',{'k1':b'k'*32},signing_key_id='k1')
    assert {'execute','mutate','promote','rollback','acquire','release'}.isdisjoint(dir(ring))

def test_authenticated_append_failure_fails_closed_but_supervisor_constructs(monkeypatch,tmp_path):
    journal,_=seed(tmp_path); auth=HMACRecoveryAuthenticator('producer',b'a'*32,key_id='k1'); c=cfg(tmp_path,journal,auth)
    def boom(*args,**kwargs): raise OSError('simulated auth append failure')
    monkeypatch.setattr('infrastructure_loop.AuthenticatedRecoveryChain.append',boom)
    loop=InfrastructureSupervisoryLoop([],config=c)
    assert loop._recovered_proof_transactions==()
    # Integrity chain may have advanced, but missing authenticated evidence can never restore trust.
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==1


def test_v30_crash_after_integrity_append_reconciles_next_startup(monkeypatch,tmp_path):
    from recovery_transaction import RecoveryDualChainCoordinator
    journal,tx=seed(tmp_path); auth=HMACRecoveryAuthenticator('producer',b'a'*32,key_id='k1'); c=cfg(tmp_path,journal,auth)
    original=AuthenticatedRecoveryChain.append
    calls={'n':0}
    def fail_once(self,*args,**kwargs):
        calls['n']+=1
        if calls['n']==1: raise OSError('simulated crash after integrity append')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(AuthenticatedRecoveryChain,'append',fail_once)
    first=InfrastructureSupervisoryLoop([],config=c)
    assert first._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==1
    monkeypatch.setattr(AuthenticatedRecoveryChain,'append',original)
    second=InfrastructureSupervisoryLoop([],config=c)
    assert [x.transaction_hash for x in second._recovered_proof_transactions]==[tx.transaction_hash]
    base=AppendOnlyRecoveryChain(tmp_path/'chain'); side=AuthenticatedRecoveryChain(tmp_path/'chain',auth)
    assert base.verify_chain().generation==2 and side.verify_against(base).valid
    assert RecoveryDualChainCoordinator(tmp_path/'chain').verify_transactions(base,side).valid


def test_v30_crash_after_both_writes_before_commit_reconciles(monkeypatch,tmp_path):
    from recovery_transaction import RecoveryDualChainCoordinator
    journal,tx=seed(tmp_path); auth=HMACRecoveryAuthenticator('producer',b'a'*32,key_id='k1'); c=cfg(tmp_path,journal,auth)
    original=RecoveryDualChainCoordinator._commit
    calls={'n':0}
    def fail_once(self,*args,**kwargs):
        calls['n']+=1
        if calls['n']==1: raise OSError('simulated crash before commit marker')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(RecoveryDualChainCoordinator,'_commit',fail_once)
    first=InfrastructureSupervisoryLoop([],config=c)
    assert first._recovered_proof_transactions==()
    base=AppendOnlyRecoveryChain(tmp_path/'chain'); side=AuthenticatedRecoveryChain(tmp_path/'chain',auth)
    assert base.verify_chain().generation==1 and side.verify_chain().generation==1
    monkeypatch.setattr(RecoveryDualChainCoordinator,'_commit',original)
    second=InfrastructureSupervisoryLoop([],config=c)
    assert [x.transaction_hash for x in second._recovered_proof_transactions]==[tx.transaction_hash]
    assert RecoveryDualChainCoordinator(tmp_path/'chain').verify_transactions(base,side).valid


def test_v30_tampered_transaction_intent_fails_closed_without_advancing(tmp_path):
    from recovery_transaction import RecoveryDualChainCoordinator
    journal,_=seed(tmp_path); auth=HMACRecoveryAuthenticator('producer',b'a'*32,key_id='k1'); c=cfg(tmp_path,journal,auth)
    InfrastructureSupervisoryLoop([],config=c)
    p=next((tmp_path/'chain').glob('txn-intent-*.json')); m=json.loads(p.read_text()); m['checkpoint_hash']='0'*64; p.write_text(json.dumps(m))
    before=AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation
    loop=InfrastructureSupervisoryLoop([],config=c)
    assert loop._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/'chain').verify_chain().generation==before


def test_v30_legacy_v29_pair_without_transaction_history_fails_closed(tmp_path):
    from recovery_policy import StartupRecoveryPolicy
    from proof_journal import ProofJournalReplayVerifier
    journal,_=seed(tmp_path); auth=HMACRecoveryAuthenticator('producer',b'a'*32,key_id='k1'); c=cfg(tmp_path,journal,auth)
    decision_now=StartupRecoveryPolicy(journal,verifier=ProofJournalReplayVerifier()).recover(now=20)
    checkpoint=__import__('recovery_checkpoint').RecoveryCheckpoint.from_decision(decision_now)
    base=AppendOnlyRecoveryChain(tmp_path/'chain'); side=AuthenticatedRecoveryChain(tmp_path/'chain',auth)
    base.append(checkpoint,fsync=False); side.append(checkpoint,fsync=False)
    loop=InfrastructureSupervisoryLoop([],config=c)
    assert loop._recovered_proof_transactions==()
    assert base.verify_chain().generation==1 and side.verify_chain().generation==1
