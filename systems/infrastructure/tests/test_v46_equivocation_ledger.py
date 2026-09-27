import json, pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_remote_history_heads import RemoteHistoryHeadSigner
from recovery_gossip_evidence import GossipReceiptSigner, EquivocationEvidenceBundle
from recovery_equivocation_ledger import EquivocationEvidenceLedger

def make_bundle(seq=1):
    peer=Ed25519RecoverySigner.generate('peer',key_id='peer-k')
    hs=RemoteHistoryHeadSigner(peer)
    a=hs.sign(peer='remote',sequence=seq,record_hash='a'*64,observed_at=100)
    b=hs.sign(peer='remote',sequence=seq,record_hash='b'*64,observed_at=101)
    o1=Ed25519RecoverySigner.generate('obs1',key_id='o1')
    o2=Ed25519RecoverySigner.generate('obs2',key_id='o2')
    return EquivocationEvidenceBundle.build(a,GossipReceiptSigner(o1).sign(a,received_at=110),b,GossipReceiptSigner(o2).sign(b,received_at=111)), {'obs1':o1.verifier(),'obs2':o2.verifier()}

def test_append_reopen_and_deduplicate(tmp_path):
    b,vs=make_bundle(); l=EquivocationEvidenceLedger(tmp_path,vs)
    r=l.append(b,now=120,fsync=False); assert l.verify_chain(now=120).valid
    with pytest.raises(ValueError,match='duplicate'): l.append(b,now=120,fsync=False)
    assert EquivocationEvidenceLedger(tmp_path,vs).verify_chain(now=120).valid

def test_tamper_and_head_rollback_fail_closed(tmp_path):
    b,vs=make_bundle(); l=EquivocationEvidenceLedger(tmp_path,vs); l.append(b,now=120,fsync=False)
    p=l.path(1); d=json.loads(p.read_text()); d['evidence_hash']='0'*64; p.write_text(json.dumps(d))
    assert not l.verify_chain(now=120).valid

def test_head_rollback_fails_closed(tmp_path):
    b,vs=make_bundle(); l=EquivocationEvidenceLedger(tmp_path,vs); l.append(b,now=120,fsync=False)
    l.head.write_text(json.dumps({'sequence':0,'entry_hash':'0'*64}))
    assert not l.verify_chain(now=120).valid

def test_invalid_bundle_never_persisted(tmp_path):
    b,vs=make_bundle(); bad=EquivocationEvidenceBundle.build(b.left_head,b.left_receipt,b.left_head,b.right_receipt)
    l=EquivocationEvidenceLedger(tmp_path,vs)
    with pytest.raises(ValueError): l.append(bad,now=120,fsync=False)
    assert list(tmp_path.glob('evidence-*.json'))==[]
