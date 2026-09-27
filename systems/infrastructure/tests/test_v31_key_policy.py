import dataclasses, json
import pytest
from durable_journal import DurableProofJournal
from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
from recovery_auth import HMACRecoveryKeyring, HMACRecoveryAuthenticator, AuthenticatedRecoveryEnvelope
from recovery_chain import AppendOnlyRecoveryChain, AuthenticatedRecoveryChain
from test_proof_journal import fixture
from recovery_key_policy import (
    RecoveryKeyPolicy, HMACRecoveryKeyPolicyAuthority, RecoveryKeyPolicyStore,
    PolicyBoundRecoveryAuthenticator
)

ROOT=b"r"*32
K1=b"a"*32
K2=b"b"*32

def authority():
    return HMACRecoveryKeyPolicyAuthority("policy-root",ROOT)

def policy(epoch, prev, effective, active, trusted, retired=(), revoked=()):
    return RecoveryKeyPolicy.issue(
        epoch=epoch, previous_policy_hash=prev, producer_id="producer",
        effective_generation=effective, active_key_id=active,
        trusted_key_ids=tuple(trusted), retired_key_ids=tuple(retired),
        revoked_key_ids=tuple(revoked),
    )

def make_store(tmp_path):
    store=RecoveryKeyPolicyStore(tmp_path/"policy",authority())
    p1=policy(1,"0"*64,1,"k1",("k1",))
    store.append(p1,fsync=False)
    return store,p1

def cfg(tmp_path,journal,auth):
    return LoopConfig(
        durable_proof_journal_path=str(journal), startup_recovery_enabled=True,
        startup_recovery_now=20, recovery_chain_dir=str(tmp_path/"chain"),
        recovery_checkpoint_fsync=False, recovery_chain_lock_timeout_seconds=.01,
        recovery_authenticator=auth,
    )

def seed(tmp_path):
    journal=tmp_path/"proof.journal"; tx=fixture()
    DurableProofJournal(journal).append(dataclasses.asdict(tx),fsync=False)
    return journal,tx

def test_policy_chain_and_rotation_are_valid(tmp_path):
    store,p1=make_store(tmp_path)
    p2=policy(2,p1.policy_hash,2,"k2",("k1","k2"),retired=("k1",))
    store.append(p2,fsync=False)
    v=store.verify_chain()
    assert v.valid and v.epoch==2
    assert store.policy_for_generation(1).epoch==1
    assert store.policy_for_generation(2).epoch==2

def test_policy_signature_tamper_fails_closed(tmp_path):
    store,_=make_store(tmp_path)
    p=tmp_path/"policy"/"key-policy-00000000000000000001.json"
    m=json.loads(p.read_text()); s=m["signature"]; m["signature"]=("1" if s[0]!="1" else "2")+s[1:]; p.write_text(json.dumps(m))
    assert not store.verify_chain().valid

def test_policy_head_rollback_replay_rejected(tmp_path):
    store,p1=make_store(tmp_path)
    old_head=(tmp_path/"policy"/"HEAD").read_text()
    p2=policy(2,p1.policy_hash,2,"k2",("k1","k2"),retired=("k1",))
    store.append(p2,fsync=False)
    (tmp_path/"policy"/"HEAD").write_text(old_head)
    assert not store.verify_chain().valid

def test_revoked_key_cannot_reappear(tmp_path):
    store,p1=make_store(tmp_path)
    p2=policy(2,p1.policy_hash,2,"k2",("k2",),revoked=("k1",))
    store.append(p2,fsync=False)
    p3=policy(3,p2.policy_hash,3,"k1",("k1","k2"))
    with pytest.raises(ValueError):
        store.append(p3,fsync=False)

def test_policy_bound_rotation_verifies_history_and_signs_new(tmp_path):
    store,p1=make_store(tmp_path)
    ring=HMACRecoveryKeyring("producer",{"k1":K1,"k2":K2},signing_key_id="k1")
    bound=PolicyBoundRecoveryAuthenticator(ring,store)
    e1=bound.sign({"generation":1,"checkpoint_hash":"x"})
    assert e1.key_id=="k1" and e1.payload["policy_epoch"]==1 and bound.verify(e1)
    p2=policy(2,p1.policy_hash,2,"k2",("k1","k2"),retired=("k1",))
    store.append(p2,fsync=False)
    assert bound.verify(e1)
    ring2=HMACRecoveryKeyring("producer",{"k1":K1,"k2":K2},signing_key_id="k2")
    bound2=PolicyBoundRecoveryAuthenticator(ring2,store)
    e2=bound2.sign({"generation":2,"checkpoint_hash":"y"})
    assert e2.key_id=="k2" and e2.payload["policy_epoch"]==2 and bound2.verify(e2)

def test_retired_key_cannot_sign_new_generation(tmp_path):
    store,p1=make_store(tmp_path)
    store.append(policy(2,p1.policy_hash,2,"k2",("k1","k2"),retired=("k1",)),fsync=False)
    old=PolicyBoundRecoveryAuthenticator(HMACRecoveryKeyring("producer",{"k1":K1,"k2":K2},signing_key_id="k1"),store)
    with pytest.raises(ValueError):
        old.sign({"generation":2})

def test_revoked_key_envelope_rejected_for_revoked_epoch(tmp_path):
    store,p1=make_store(tmp_path)
    p2=policy(2,p1.policy_hash,2,"k2",("k2",),revoked=("k1",))
    store.append(p2,fsync=False)
    raw=HMACRecoveryAuthenticator("producer",K1,key_id="k1").sign({"generation":2,"policy_epoch":2,"policy_hash":p2.policy_hash})
    bound=PolicyBoundRecoveryAuthenticator(HMACRecoveryKeyring("producer",{"k1":K1,"k2":K2},signing_key_id="k2"),store)
    assert not bound.verify(raw)

def test_unknown_future_policy_epoch_rejected(tmp_path):
    store,_=make_store(tmp_path)
    raw=HMACRecoveryAuthenticator("producer",K1,key_id="k1").sign({"generation":1,"policy_epoch":99,"policy_hash":"0"*64})
    bound=PolicyBoundRecoveryAuthenticator(HMACRecoveryKeyring("producer",{"k1":K1},signing_key_id="k1"),store)
    assert not bound.verify(raw)

def test_policy_bound_authenticator_has_no_mutation_authority(tmp_path):
    store,_=make_store(tmp_path)
    bound=PolicyBoundRecoveryAuthenticator(HMACRecoveryKeyring("producer",{"k1":K1},signing_key_id="k1"),store)
    assert {"execute","mutate","promote","rollback","acquire","release"}.isdisjoint(dir(bound))

def test_startup_rotation_uses_applicable_policy_epoch(tmp_path):
    journal,tx=seed(tmp_path); store,p1=make_store(tmp_path)
    bound1=PolicyBoundRecoveryAuthenticator(HMACRecoveryKeyring("producer",{"k1":K1,"k2":K2},signing_key_id="k1"),store)
    first=InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,bound1))
    assert first._recovered_proof_transactions==()
    p2=policy(2,p1.policy_hash,2,"k2",("k1","k2"),retired=("k1",))
    store.append(p2,fsync=False)
    bound2=PolicyBoundRecoveryAuthenticator(HMACRecoveryKeyring("producer",{"k1":K1,"k2":K2},signing_key_id="k2"),store)
    second=InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,bound2))
    assert [x.transaction_hash for x in second._recovered_proof_transactions]==[tx.transaction_hash]
    m=json.loads((tmp_path/"chain"/"auth-00000000000000000002.json").read_text())
    assert m["envelope"]["key_id"]=="k2"
    assert m["envelope"]["payload"]["policy_epoch"]==2

def test_policy_tamper_at_startup_fails_closed_without_advancing(tmp_path):
    journal,_=seed(tmp_path); store,_=make_store(tmp_path)
    bound=PolicyBoundRecoveryAuthenticator(HMACRecoveryKeyring("producer",{"k1":K1},signing_key_id="k1"),store)
    c=cfg(tmp_path,journal,bound)
    InfrastructureSupervisoryLoop([],config=c)
    before=AppendOnlyRecoveryChain(tmp_path/"chain").verify_chain().generation
    p=tmp_path/"policy"/"key-policy-00000000000000000001.json"
    m=json.loads(p.read_text()); m["policy"]["active_key_id"]="evil"; p.write_text(json.dumps(m))
    loop=InfrastructureSupervisoryLoop([],config=c)
    assert loop._recovered_proof_transactions==()
    assert AppendOnlyRecoveryChain(tmp_path/"chain").verify_chain().generation==before

def test_policy_components_have_no_mutation_authority(tmp_path):
    store,_=make_store(tmp_path)
    objects=[authority(),store,PolicyBoundRecoveryAuthenticator(
        HMACRecoveryKeyring("producer",{"k1":K1},signing_key_id="k1"),store)]
    forbidden={"execute","mutate","promote","rollback","acquire","release"}
    for obj in objects:
        assert forbidden.isdisjoint(dir(obj))
