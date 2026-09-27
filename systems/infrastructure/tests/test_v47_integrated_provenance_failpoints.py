import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_remote_history_heads import RemoteHistoryHeadSigner,RemoteHistoryHeadVerifier
from recovery_remote_head_chain import SignedRemoteHeadChain
from recovery_gossip_evidence import GossipReceiptSigner
from recovery_head_gossip_provenance import WitnessedRemoteHeadChain
from recovery_authority_governance import AuthoritySetEpoch
from recovery_authority_transaction import CrashReconciledAuthoritySetStore
from recovery_governance_quorum import GovernanceApprovalSigner

def signer(name): return Ed25519RecoverySigner.generate(name,key_id=name+'-k')

def test_witnessed_chain_binds_receipt_to_persisted_entry(tmp_path):
 p=signer('peer'); o=signer('observer'); v=RemoteHistoryHeadVerifier(p.verifier())
 wc=WitnessedRemoteHeadChain(tmp_path,v,o.verifier())
 h=RemoteHistoryHeadSigner(p).sign(peer='log',sequence=1,record_hash='a'*64,observed_at=100)
 r=GossipReceiptSigner(o).sign(h,received_at=101)
 prov=wc.append(h,r,now=102,fsync=False)
 assert prov.sequence==1 and wc.verify_chain(now=102).valid

def test_witnessed_chain_rejects_receipt_substitution_before_append(tmp_path):
 p=signer('peer'); o=signer('observer'); v=RemoteHistoryHeadVerifier(p.verifier()); wc=WitnessedRemoteHeadChain(tmp_path,v,o.verifier())
 h=RemoteHistoryHeadSigner(p).sign(peer='log',sequence=1,record_hash='a'*64,observed_at=100)
 other=RemoteHistoryHeadSigner(p).sign(peer='log',sequence=1,record_hash='b'*64,observed_at=100)
 r=GossipReceiptSigner(o).sign(other,received_at=101)
 with pytest.raises(ValueError): wc.append(h,r,now=102,fsync=False)
 assert list(tmp_path.glob('head-*.json'))==[]

def setup_auth(tmp_path):
 ss=[signer('a'+str(i)) for i in range(3)]; st=CrashReconciledAuthoritySetStore(tmp_path)
 e1=AuthoritySetEpoch.issue(epoch=1,previous_epoch_hash='0'*64,effective_governance_epoch=1,threshold=2,authority_verifiers=[x.verifier() for x in ss]); st.bootstrap(e1,fsync=False)
 e2=AuthoritySetEpoch.issue(epoch=2,previous_epoch_hash=e1.epoch_hash,effective_governance_epoch=2,threshold=2,authority_verifiers=[x.verifier() for x in ss]); ap=[GovernanceApprovalSigner(x).approve(2,e2.epoch_hash) for x in ss[:2]]
 return st,e2,ap

def test_transaction_payload_write_failpoint_leaves_no_pending_state(tmp_path):
 st,e,ap=setup_auth(tmp_path)
 with pytest.raises(RuntimeError): st.append(e,ap,fsync=False,fail_after='TXN_PAYLOAD_WRITTEN')
 assert not st.txn.exists(); assert st.verify_chain().valid

def test_transition_record_failpoint_recovers(tmp_path):
 st,e,ap=setup_auth(tmp_path)
 with pytest.raises(RuntimeError): st.append(e,ap,fsync=False,fail_after='TRANSITION_RECORD_WRITTEN')
 assert not st.verify_chain().valid
 st.recover(fsync=False); assert st.verify_chain().valid

def test_txn_unlink_failpoint_recovery_is_idempotent(tmp_path):
 st,e,ap=setup_auth(tmp_path)
 with pytest.raises(RuntimeError): st.append(e,ap,fsync=False,fail_after='TXN_UNLINKED')
 assert st.verify_chain().valid
 assert st.recover(fsync=False).valid
