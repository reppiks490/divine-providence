import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_governance_quorum import GovernanceApprovalSigner,GovernanceAuthorityQuorum
from recovery_governance_admission import AtomicGovernanceAdmissionStore

def ss(n=3): return [Ed25519RecoverySigner.generate(f"ga{i}",key_id=f"k{i}") for i in range(n)]
def test_admit_requires_quorum(tmp_path):
 s=ss(); q=GovernanceAuthorityQuorum([x.verifier() for x in s],2); st=AtomicGovernanceAdmissionStore(tmp_path,q)
 a=[GovernanceApprovalSigner(x).approve(1,"a"*64) for x in s[:2]]
 st.admit(1,"a"*64,a,fsync=False); assert st.verify_chain().valid
def test_partial_quorum_rejected(tmp_path):
 s=ss(); q=GovernanceAuthorityQuorum([x.verifier() for x in s],2); st=AtomicGovernanceAdmissionStore(tmp_path,q)
 with pytest.raises(ValueError): st.admit(1,"a"*64,[GovernanceApprovalSigner(s[0]).approve(1,"a"*64)],fsync=False)
def test_replay_and_substitution_rejected(tmp_path):
 s=ss(); q=GovernanceAuthorityQuorum([x.verifier() for x in s],2); st=AtomicGovernanceAdmissionStore(tmp_path,q)
 a=[GovernanceApprovalSigner(x).approve(1,"a"*64) for x in s[:2]]; st.admit(1,"a"*64,a,fsync=False)
 with pytest.raises((ValueError,FileExistsError)): st.admit(1,"b"*64,a,fsync=False)
def test_head_tamper_fails_closed(tmp_path):
 s=ss(); q=GovernanceAuthorityQuorum([x.verifier() for x in s],2); st=AtomicGovernanceAdmissionStore(tmp_path,q)
 a=[GovernanceApprovalSigner(x).approve(1,"a"*64) for x in s[:2]]; st.admit(1,"a"*64,a,fsync=False)
 (tmp_path/"HEAD").write_text('{"epoch":0,"record_hash":"'+"0"*64+'"}')
 assert not st.verify_chain().valid
def test_no_mutation_authority(tmp_path):
 s=ss(); q=GovernanceAuthorityQuorum([x.verifier() for x in s],2); st=AtomicGovernanceAdmissionStore(tmp_path,q)
 assert {"execute","mutate","promote","rollback","acquire","release"}.isdisjoint(dir(st))
