import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_remote_history_heads import RemoteHistoryHeadSigner, RemoteHistoryHeadVerifier
from recovery_gossip_evidence import GossipReceiptSigner
from recovery_atomic_witnessed_provenance import AtomicWitnessedProvenanceStore


def setup(tmp_path):
    peer=Ed25519RecoverySigner.generate('peer',key_id='pk'); obs=Ed25519RecoverySigner.generate('obs',key_id='ok')
    hv=RemoteHistoryHeadVerifier(peer.verifier(),max_future_skew_seconds=0)
    s=AtomicWitnessedProvenanceStore(tmp_path,hv,obs.verifier())
    return s,RemoteHistoryHeadSigner(peer),GossipReceiptSigner(obs)

def pair(hs,rs,n,t):
    h=hs.sign(peer='remote',sequence=n,record_hash=f'{n:064x}',observed_at=t)
    return h,rs.sign(h,received_at=t)

def test_normal_commit_and_reopen(tmp_path):
    s,hs,rs=setup(tmp_path); h,r=pair(hs,rs,1,101)
    v=s.admit(h,r,now=101); assert v.valid and v.sequence==1
    assert AtomicWitnessedProvenanceStore(tmp_path,s.head_verifier,s.observer_verifier).verify(now=200).valid

def test_head_written_provenance_missing_recovers_idempotently(tmp_path):
    s,hs,rs=setup(tmp_path); h,r=pair(hs,rs,1,101)
    with pytest.raises(RuntimeError): s.admit(h,r,now=101,fail_after='HEAD_WRITTEN')
    assert s.head_chain.verify_chain(now=200).valid
    assert s.provenance.verify_chain(now=200,allow_empty=True).sequence==0
    v=s.recover(now=200); assert v.valid and v.sequence==1
    assert s.recover(now=200).valid and s.provenance.verify_chain(now=200).sequence==1

def test_prepared_recovery_and_replay_rejected(tmp_path):
    s,hs,rs=setup(tmp_path); h,r=pair(hs,rs,1,101)
    with pytest.raises(RuntimeError): s.admit(h,r,now=101,fail_after='PREPARED')
    assert s.recover(now=200).valid
    with pytest.raises(ValueError): s.admit(h,r,now=200)

def test_payload_tamper_fails_closed(tmp_path):
    s,hs,rs=setup(tmp_path); h,r=pair(hs,rs,1,101)
    with pytest.raises(RuntimeError): s.admit(h,r,now=101,fail_after='PREPARED')
    import json
    x=json.loads(s.txn_path.read_text()); x['receipt']['observer_id']='evil'; s.txn_path.write_text(json.dumps(x))
    assert not s.recover(now=200).valid
