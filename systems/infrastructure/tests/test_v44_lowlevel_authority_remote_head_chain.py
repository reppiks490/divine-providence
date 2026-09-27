import json, pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_authority_governance import AuthoritySetEpoch, AuthoritySetStore, GEN
from recovery_remote_history_heads import RemoteHistoryHeadSigner, RemoteHistoryHeadVerifier
from recovery_remote_head_chain import SignedRemoteHeadChain

def signer(name): return Ed25519RecoverySigner.generate(name,key_id=name+'-key')
def epoch(n, prev, effective, threshold, ss): return AuthoritySetEpoch.issue(epoch=n,previous_epoch_hash=prev,effective_governance_epoch=effective,threshold=threshold,authority_verifiers=[s.verifier() for s in ss])

def test_authority_store_record_head_torn_write_repair(tmp_path):
    ss=[signer('a'),signer('b')]; st=AuthoritySetStore(tmp_path/'a')
    e=epoch(1,GEN,1,1,ss)
    with pytest.raises(RuntimeError): st.append(e,fsync=False,fail_after='RECORD_WRITTEN')
    assert st.path(1).exists() and not st.head.exists()
    assert not st.verify_chain().valid
    assert st.repair_head(fsync=False).valid
    assert st.verify_chain().valid

def test_authority_store_stale_head_repair_only_when_records_valid(tmp_path):
    ss=[signer('a')]; st=AuthoritySetStore(tmp_path/'a'); e=epoch(1,GEN,1,1,ss); st.append(e,fsync=False)
    st.head.write_text(json.dumps({'epoch':0,'epoch_hash':'0'*64}))
    assert not st.verify_chain().valid
    assert st.repair_head(fsync=False).valid
    st.path(1).write_text('{}')
    with pytest.raises(ValueError): st.repair_head(fsync=False)

def test_signed_remote_head_chain_append_and_reopen(tmp_path):
    s=signer('peer-signer'); sg=RemoteHistoryHeadSigner(s); vf=RemoteHistoryHeadVerifier(s.verifier(),max_future_skew_seconds=5)
    ch=SignedRemoteHeadChain(tmp_path/'heads',vf)
    h1=sg.sign(peer='peer1',sequence=1,record_hash='a'*64,observed_at=100)
    h2=sg.sign(peer='peer1',sequence=2,record_hash='b'*64,observed_at=101)
    ch.append(h1,now=100,fsync=False); ch.append(h2,now=101,fsync=False)
    assert ch.verify_chain(now=101).valid and ch.verify_chain(now=101).sequence==2

def test_remote_head_chain_rejects_tamper_and_head_rollback(tmp_path):
    s=signer('peer-signer'); sg=RemoteHistoryHeadSigner(s); vf=RemoteHistoryHeadVerifier(s.verifier())
    ch=SignedRemoteHeadChain(tmp_path/'heads',vf); h=sg.sign(peer='peer1',sequence=1,record_hash='a'*64,observed_at=100); ch.append(h,now=100,fsync=False)
    ch.head.write_text(json.dumps({'sequence':0,'entry_hash':'0'*64}))
    assert not ch.verify_chain(now=100).valid

def test_remote_head_chain_temporal_split_view(tmp_path):
    s1=signer('log1'); s2=signer('log2')
    c1=SignedRemoteHeadChain(tmp_path/'l1',RemoteHistoryHeadVerifier(s1.verifier()))
    c2=SignedRemoteHeadChain(tmp_path/'l2',RemoteHistoryHeadVerifier(s2.verifier()))
    c1.append(RemoteHistoryHeadSigner(s1).sign(peer='shared',sequence=1,record_hash='a'*64,observed_at=100),now=100,fsync=False)
    c2.append(RemoteHistoryHeadSigner(s2).sign(peer='shared',sequence=1,record_hash='b'*64,observed_at=100),now=100,fsync=False)
    v=c1.compare_latest(c2,now=100)
    assert not v.valid and v.equivocation
