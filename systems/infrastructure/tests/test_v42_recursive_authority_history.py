import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_governance_quorum import GovernanceApprovalSigner, TransparencyAnchorSigner, TransparencyAnchorQuorum, FreshnessPolicy
from recovery_authority_governance import AuthoritySetEpoch
from recovery_authority_transition import GovernedAuthoritySetStore
from recovery_remote_transparency import RemoteTransparencyHistory
from recovery_transparency_history_import import VerifiedRemoteHistoryImporter

def ss(prefix,n): return [Ed25519RecoverySigner.generate(f'{prefix}{i}',key_id=f'{prefix}k{i}') for i in range(n)]
def epoch(n,prev,effective,threshold,signers): return AuthoritySetEpoch.issue(epoch=n,previous_epoch_hash=prev,effective_governance_epoch=effective,threshold=threshold,authority_verifiers=[s.verifier() for s in signers])

def test_genesis_bootstrap_then_previous_quorum_approves_successor(tmp_path):
 a=ss('a',3); st=GovernedAuthoritySetStore(tmp_path/'auth')
 e1=epoch(1,'0'*64,1,2,a); st.bootstrap(e1,fsync=False)
 b=[a[0],a[1],ss('b',1)[0]]; e2=epoch(2,e1.epoch_hash,2,2,b)
 approvals=[GovernanceApprovalSigner(s).approve(2,e2.epoch_hash) for s in a[:2]]
 st.append(e2,approvals,fsync=False); assert st.verify_chain().valid

def test_partial_previous_quorum_rejected(tmp_path):
 a=ss('a',3); st=GovernedAuthoritySetStore(tmp_path/'auth'); e1=epoch(1,'0'*64,1,2,a); st.bootstrap(e1,fsync=False)
 e2=epoch(2,e1.epoch_hash,2,2,a)
 with pytest.raises(ValueError): st.append(e2,[GovernanceApprovalSigner(a[0]).approve(2,e2.epoch_hash)],fsync=False)

def test_new_authority_cannot_approve_its_own_substitution(tmp_path):
 a=ss('a',3); st=GovernedAuthoritySetStore(tmp_path/'auth'); e1=epoch(1,'0'*64,1,2,a); st.bootstrap(e1,fsync=False)
 x=ss('x',1)[0]; nxt=[a[0],a[1],x]; e2=epoch(2,e1.epoch_hash,2,2,nxt)
 approvals=[GovernanceApprovalSigner(a[0]).approve(2,e2.epoch_hash),GovernanceApprovalSigner(x).approve(2,e2.epoch_hash)]
 with pytest.raises(ValueError): st.append(e2,approvals,fsync=False)

def test_transition_approval_tamper_detected_on_reopen(tmp_path):
 a=ss('a',3); st=GovernedAuthoritySetStore(tmp_path/'auth'); e1=epoch(1,'0'*64,1,2,a); st.bootstrap(e1,fsync=False)
 e2=epoch(2,e1.epoch_hash,2,2,a); approvals=[GovernanceApprovalSigner(s).approve(2,e2.epoch_hash) for s in a[:2]]; st.append(e2,approvals,fsync=False)
 p=tmp_path/'auth'/'transition-00000000000000000002.json'; p.write_text(p.read_text().replace(e2.epoch_hash,'f'*64,1)); assert not st.verify_chain().valid

def test_verified_remote_import_only_after_anchor_quorum_and_freshness(tmp_path):
 anchors=ss('log',3); q=TransparencyAnchorQuorum([s.verifier() for s in anchors],2); hist=RemoteTransparencyHistory(tmp_path/'hist')
 imp=VerifiedRemoteHistoryImporter(hist,q,FreshnessPolicy(60,5)); d={'sequence':1,'checkpoint_hash':'c'*64,'observed_at':1000}; r=[TransparencyAnchorSigner(s).anchor(1,'c'*64,1000) for s in anchors[:2]]
 imp.admit('peerA',d,r,now=1010,fsync=False); assert hist.verify_peer('peerA').valid

def test_verified_remote_import_rejects_partial_or_stale_without_history_write(tmp_path):
 anchors=ss('log',3); q=TransparencyAnchorQuorum([s.verifier() for s in anchors],2); hist=RemoteTransparencyHistory(tmp_path/'hist'); imp=VerifiedRemoteHistoryImporter(hist,q,FreshnessPolicy(60,5)); d={'sequence':1,'checkpoint_hash':'c'*64,'observed_at':1000}
 with pytest.raises(ValueError): imp.admit('peerA',d,[TransparencyAnchorSigner(anchors[0]).anchor(1,'c'*64,1000)],now=1010,fsync=False)
 with pytest.raises(ValueError): imp.admit('peerA',d,[TransparencyAnchorSigner(s).anchor(1,'c'*64,1000) for s in anchors[:2]],now=1061,fsync=False)
 assert hist.verify_peer('peerA',allow_empty=True).valid

def test_cross_log_disagreement_survives_verified_import(tmp_path):
 anchors=ss('log',3); q=TransparencyAnchorQuorum([s.verifier() for s in anchors],2); hist=RemoteTransparencyHistory(tmp_path/'hist'); imp=VerifiedRemoteHistoryImporter(hist,q,FreshnessPolicy(60,5))
 for peer,h in [('p1','a'*64),('p2','b'*64)]:
  d={'sequence':1,'checkpoint_hash':h,'observed_at':1000}; r=[TransparencyAnchorSigner(s).anchor(1,h,1000) for s in anchors[:2]]; imp.admit(peer,d,r,now=1010,fsync=False)
 v=hist.compare_sequence(1); assert not v.valid and v.equivocation
