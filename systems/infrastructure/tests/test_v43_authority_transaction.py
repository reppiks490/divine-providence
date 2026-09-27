import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_governance_quorum import GovernanceApprovalSigner
from recovery_authority_governance import AuthoritySetEpoch
from recovery_authority_transaction import CrashReconciledAuthoritySetStore

def ss(n=3): return [Ed25519RecoverySigner.generate(f'a{i}',key_id=f'k{i}') for i in range(n)]
def ep(n,prev,sg): return AuthoritySetEpoch.issue(epoch=n,previous_epoch_hash=prev,effective_governance_epoch=n,threshold=2,authority_verifiers=[s.verifier() for s in sg])
def setup(tmp_path):
 s=ss(); st=CrashReconciledAuthoritySetStore(tmp_path/'auth'); e1=ep(1,'0'*64,s); st.bootstrap(e1,fsync=False); return s,st,e1

def test_authority_transition_commits(tmp_path):
 s,st,e1=setup(tmp_path); e2=ep(2,e1.epoch_hash,s); a=[GovernanceApprovalSigner(x).approve(2,e2.epoch_hash) for x in s[:2]]
 st.append(e2,a,fsync=False); assert st.verify_chain().valid and st.verify_chain().epoch==2

def test_crash_after_prepared_recovers_idempotently(tmp_path):
 s,st,e1=setup(tmp_path); e2=ep(2,e1.epoch_hash,s); a=[GovernanceApprovalSigner(x).approve(2,e2.epoch_hash) for x in s[:2]]
 with pytest.raises(RuntimeError): st.append(e2,a,fsync=False,fail_after='PREPARED')
 st2=CrashReconciledAuthoritySetStore(tmp_path/'auth'); st2.recover(fsync=False); st2.recover(fsync=False); assert st2.verify_chain().valid and st2.verify_chain().epoch==2

def test_crash_after_transition_evidence_recovers(tmp_path):
 s,st,e1=setup(tmp_path); e2=ep(2,e1.epoch_hash,s); a=[GovernanceApprovalSigner(x).approve(2,e2.epoch_hash) for x in s[:2]]
 with pytest.raises(RuntimeError): st.append(e2,a,fsync=False,fail_after='TRANSITION_WRITTEN')
 st2=CrashReconciledAuthoritySetStore(tmp_path/'auth'); st2.recover(fsync=False); assert st2.verify_chain().valid

def test_partial_quorum_never_prepares(tmp_path):
 s,st,e1=setup(tmp_path); e2=ep(2,e1.epoch_hash,s)
 with pytest.raises(ValueError): st.append(e2,[GovernanceApprovalSigner(s[0]).approve(2,e2.epoch_hash)],fsync=False)
 assert not (tmp_path/'auth'/'TXN.json').exists()

def test_payload_tamper_blocks_recovery(tmp_path):
 s,st,e1=setup(tmp_path); e2=ep(2,e1.epoch_hash,s); a=[GovernanceApprovalSigner(x).approve(2,e2.epoch_hash) for x in s[:2]]
 with pytest.raises(RuntimeError): st.append(e2,a,fsync=False,fail_after='PREPARED')
 p=tmp_path/'auth'/'TXN.json'; p.write_text(p.read_text().replace(e2.epoch_hash,'f'*64,1))
 with pytest.raises(ValueError): CrashReconciledAuthoritySetStore(tmp_path/'auth').recover(fsync=False)
