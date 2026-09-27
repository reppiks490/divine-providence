import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_witness_governance import GossipVerdict
from recovery_governance_quorum import (
    GovernanceApproval, GovernanceApprovalSigner, GovernanceAuthorityQuorum,
    TransparencyAnchorReceipt, TransparencyAnchorSigner, TransparencyAnchorQuorum,
    FreshnessPolicy, verify_received_checkpoint,
)

def signers(prefix,n):
    return [Ed25519RecoverySigner.generate(f"{prefix}{i}",key_id=f"{prefix}{i}") for i in range(1,n+1)]

def test_governance_m_of_n_accepts_distinct_two_of_three():
    ss=signers("g",3); q=GovernanceAuthorityQuorum([s.verifier() for s in ss],2)
    approvals=[GovernanceApprovalSigner(s).approve(7,"a"*64) for s in ss[:2]]
    v=q.verify(7,"a"*64,approvals)
    assert v.valid and v.count==2

def test_governance_partial_quorum_rejected():
    ss=signers("g",3); q=GovernanceAuthorityQuorum([s.verifier() for s in ss],2)
    assert not q.verify(7,"a"*64,[GovernanceApprovalSigner(ss[0]).approve(7,"a"*64)]).valid

def test_governance_duplicate_authority_cannot_inflate_quorum():
    ss=signers("g",3); q=GovernanceAuthorityQuorum([s.verifier() for s in ss],2)
    a=GovernanceApprovalSigner(ss[0]).approve(7,"a"*64)
    assert not q.verify(7,"a"*64,[a,a]).valid

def test_governance_authority_substitution_rejected():
    ss=signers("g",3); evil=signers("evil",1)[0]
    q=GovernanceAuthorityQuorum([s.verifier() for s in ss],2)
    approvals=[GovernanceApprovalSigner(ss[0]).approve(7,"a"*64),GovernanceApprovalSigner(evil).approve(7,"a"*64)]
    assert not q.verify(7,"a"*64,approvals).valid

def test_governance_wrong_epoch_or_hash_rejected():
    ss=signers("g",2); q=GovernanceAuthorityQuorum([s.verifier() for s in ss],2)
    approvals=[GovernanceApprovalSigner(s).approve(7,"a"*64) for s in ss]
    assert not q.verify(8,"a"*64,approvals).valid
    assert not q.verify(7,"b"*64,approvals).valid

def test_transparency_anchor_two_of_three_accepts():
    ss=signers("log",3); q=TransparencyAnchorQuorum([s.verifier() for s in ss],2)
    receipts=[TransparencyAnchorSigner(s).anchor(11,"c"*64,1000) for s in ss[:2]]
    v=q.verify(11,"c"*64,receipts)
    assert v.valid and v.count==2

def test_transparency_anchor_fork_same_sequence_detected():
    s=signers("log",1)[0]; signer=TransparencyAnchorSigner(s)
    q=TransparencyAnchorQuorum([s.verifier()],1)
    receipts=[signer.anchor(11,"c"*64,1000),signer.anchor(11,"d"*64,1001)]
    v=q.verify(11,"c"*64,receipts)
    assert not v.valid and v.equivocation

def test_transparency_anchor_substitution_rejected():
    good=signers("log",2); evil=signers("evil",1)[0]
    q=TransparencyAnchorQuorum([s.verifier() for s in good],2)
    receipts=[TransparencyAnchorSigner(good[0]).anchor(11,"c"*64,1000),TransparencyAnchorSigner(evil).anchor(11,"c"*64,1000)]
    assert not q.verify(11,"c"*64,receipts).valid

def test_received_checkpoint_freshness_accepts_current_and_rejects_expired():
    policy=FreshnessPolicy(max_age_seconds=60,max_future_skew_seconds=5)
    assert verify_received_checkpoint({"sequence":4,"checkpoint_hash":"a"*64,"observed_at":1000},now=1050,policy=policy).valid
    v=verify_received_checkpoint({"sequence":4,"checkpoint_hash":"a"*64,"observed_at":1000},now=1061,policy=policy)
    assert not v.valid and v.stale

def test_received_checkpoint_rejects_future_timestamp_and_rollback():
    policy=FreshnessPolicy(max_age_seconds=60,max_future_skew_seconds=5)
    assert not verify_received_checkpoint({"sequence":4,"checkpoint_hash":"a"*64,"observed_at":1010},now=1000,policy=policy).valid
    v=verify_received_checkpoint({"sequence":3,"checkpoint_hash":"a"*64,"observed_at":1000},now=1000,policy=policy,minimum_sequence=4)
    assert not v.valid and v.rollback

def test_evidence_components_have_no_mutation_authority():
    s=signers("g",2); objs=[GovernanceApprovalSigner(s[0]),GovernanceAuthorityQuorum([x.verifier() for x in s],2)]
    forbidden={"execute","mutate","promote","rollback","acquire","release"}
    for obj in objs: assert forbidden.isdisjoint(dir(obj))
