import json
import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_remote_history_heads import RemoteHistoryHeadSigner, RemoteHistoryHeadVerifier
from recovery_gossip_evidence import GossipReceiptSigner
from recovery_head_gossip_provenance import WitnessedRemoteHeadChain
from recovery_provenance_index import ProvenanceIndex


def setup(tmp_path):
    peer=Ed25519RecoverySigner.generate('peer',key_id='pk'); obs=Ed25519RecoverySigner.generate('obs',key_id='ok')
    hv=RemoteHistoryHeadVerifier(peer.verifier(),max_future_skew_seconds=0)
    wc=WitnessedRemoteHeadChain(tmp_path/'heads',hv,obs.verifier())
    idx=ProvenanceIndex(tmp_path/'prov',wc.chain,obs.verifier())
    hs=RemoteHistoryHeadSigner(peer); rs=GossipReceiptSigner(obs)
    return wc,idx,hs,rs

def admit(wc,idx,hs,rs,n,now=100):
    h=hs.sign(peer='remote',sequence=n,record_hash=f'{n:064x}',observed_at=now+n)
    r=rs.sign(h,received_at=now+n)
    p=wc.append(h,r,now=now+n)
    return h,r,idx.append(h,r,p,now=now+n)

def test_append_reopen_and_exact_chain_binding(tmp_path):
    wc,idx,hs,rs=setup(tmp_path); h,r,e=admit(wc,idx,hs,rs,1)
    assert e['head_entry_hash']==wc.chain._read_entry(1)['entry_hash']
    assert ProvenanceIndex(tmp_path/'prov',wc.chain,rs.s.verifier()).verify_chain(now=200).valid

def test_receipt_or_head_substitution_fails_before_persist(tmp_path):
    wc,idx,hs,rs=setup(tmp_path); h,r,_=admit(wc,idx,hs,rs,1)
    h2=hs.sign(peer='remote',sequence=2,record_hash='2'*64,observed_at=102); r2=rs.sign(h2,received_at=102); p2=wc.append(h2,r2,now=102)
    with pytest.raises(ValueError): idx.append(h2,r,p2,now=102)
    assert idx.verify_chain(now=200).sequence==1

def test_duplicate_provenance_rejected(tmp_path):
    wc,idx,hs,rs=setup(tmp_path); h,r,_=admit(wc,idx,hs,rs,1)
    p=wc.append(hs.sign(peer='remote',sequence=2,record_hash='2'*64,observed_at=102),rs.sign(hs.sign(peer='remote',sequence=2,record_hash='2'*64,observed_at=102),received_at=102),now=102) if False else None
    with pytest.raises(ValueError): idx.append(h,r,type('P',(),{'sequence':1,'entry_hash':wc.chain._read_entry(1)['entry_hash'],'remote_head_hash':r.remote_head_hash,'observer_id':r.observer_id})(),now=200)

def test_head_rollback_and_entry_tamper_fail_closed(tmp_path):
    wc,idx,hs,rs=setup(tmp_path); admit(wc,idx,hs,rs,1); admit(wc,idx,hs,rs,2)
    idx.head.write_text(json.dumps({'sequence':1,'entry_hash':json.loads(idx.path(1).read_text())['entry_hash']}))
    assert not idx.verify_chain(now=200).valid
    idx.head.write_text(json.dumps({'sequence':2,'entry_hash':json.loads(idx.path(2).read_text())['entry_hash']}))
    x=json.loads(idx.path(2).read_text()); x['observer_id']='evil'; idx.path(2).write_text(json.dumps(x))
    assert not idx.verify_chain(now=200).valid

def test_underlying_remote_head_chain_tamper_invalidates_provenance(tmp_path):
    wc,idx,hs,rs=setup(tmp_path); admit(wc,idx,hs,rs,1)
    x=wc.chain._read_entry(1); x['signed_head']['record_hash']='f'*64; wc.chain.path(1).write_text(json.dumps(x))
    assert not idx.verify_chain(now=200).valid
