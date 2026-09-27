import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_authority_governance import AuthoritySetEpoch
from recovery_authority_transaction import CrashReconciledAuthoritySetStore
from recovery_governance_quorum import GovernanceApprovalSigner
from recovery_remote_history_heads import RemoteHistoryHeadSigner,RemoteHistoryHeadVerifier
from recovery_gossip_evidence import GossipReceiptSigner,GossipReceiptVerifier,EquivocationEvidenceBundle

def ss(prefix,n): return [Ed25519RecoverySigner.generate(f'{prefix}{i}',key_id=f'{prefix}{i}') for i in range(1,n+1)]
def setup_store(tmp_path):
 s=ss('a',3); st=CrashReconciledAuthoritySetStore(tmp_path/'auth')
 e1=AuthoritySetEpoch.issue(epoch=1,previous_epoch_hash='0'*64,effective_governance_epoch=1,threshold=2,authority_verifiers=[x.verifier() for x in s]); st.bootstrap(e1,fsync=False)
 e2=AuthoritySetEpoch.issue(epoch=2,previous_epoch_hash=e1.epoch_hash,effective_governance_epoch=2,threshold=2,authority_verifiers=[x.verifier() for x in s])
 ap=[GovernanceApprovalSigner(x).approve(2,e2.epoch_hash) for x in s[:2]]
 return st,e2,ap

def test_composite_recovers_authority_record_without_head(tmp_path):
 st,e,ap=setup_store(tmp_path)
 with pytest.raises(RuntimeError): st.append(e,ap,fsync=False,fail_after='AUTHORITY_RECORD_WRITTEN')
 assert not st.verify_chain().valid
 st.recover(fsync=False)
 assert st.verify_chain().valid

def test_composite_head_written_failure_recovers_idempotently(tmp_path):
 st,e,ap=setup_store(tmp_path)
 with pytest.raises(RuntimeError): st.append(e,ap,fsync=False,fail_after='AUTHORITY_HEAD_WRITTEN')
 st.recover(fsync=False)
 assert st.recover(fsync=False).valid

def test_gossip_receipt_cross_signs_exact_remote_head():
 peer=ss('peer',1)[0]; observer=ss('observer',1)[0]
 h=RemoteHistoryHeadSigner(peer).sign(peer='logA',sequence=3,record_hash='a'*64,observed_at=100)
 r=GossipReceiptSigner(observer).sign(h,received_at=105)
 assert GossipReceiptVerifier(observer.verifier()).verify(r,h,now=106).valid

def test_gossip_receipt_rejects_head_substitution():
 peer=ss('peer',1)[0]; observer=ss('observer',1)[0]
 h=RemoteHistoryHeadSigner(peer).sign(peer='logA',sequence=3,record_hash='a'*64,observed_at=100)
 h2=RemoteHistoryHeadSigner(peer).sign(peer='logA',sequence=3,record_hash='b'*64,observed_at=100)
 r=GossipReceiptSigner(observer).sign(h,received_at=105)
 assert not GossipReceiptVerifier(observer.verifier()).verify(r,h2,now=106).valid

def test_equivocation_bundle_requires_conflicting_same_peer_sequence():
 peer=ss('peer',1)[0]; o1,o2=ss('observer',2)
 hs=RemoteHistoryHeadSigner(peer); a=hs.sign(peer='logA',sequence=3,record_hash='a'*64,observed_at=100); b=hs.sign(peer='logA',sequence=3,record_hash='b'*64,observed_at=101)
 ra=GossipReceiptSigner(o1).sign(a,received_at=105); rb=GossipReceiptSigner(o2).sign(b,received_at=106)
 bundle=EquivocationEvidenceBundle.build(a,ra,b,rb)
 assert bundle.verify({o1.producer_id:o1.verifier(),o2.producer_id:o2.verifier()},now=107).valid
