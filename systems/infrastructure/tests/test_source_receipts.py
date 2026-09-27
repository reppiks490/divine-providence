import dataclasses
from source_receipts import DecisionReceipt, SourceNativeEnvelopeAssembler
from proof_envelope import ProofEnvelopeVerifier, STAGE_ORDER


def receipts(identity="act-1"):
    return tuple(DecisionReceipt.issue(stage=s, action_identity=identity, issued_at=100+i,
        payload={"stage": s, "approved": True}) for i,s in enumerate(STAGE_ORDER))


def test_source_receipts_assemble_to_verifiable_v9_envelope():
    result = SourceNativeEnvelopeAssembler().assemble(receipts(), now=110)
    assert result.valid
    assert ProofEnvelopeVerifier().verify(result.envelope, now=110).valid


def test_missing_stage_is_not_reconstructed():
    result = SourceNativeEnvelopeAssembler().assemble(receipts()[:-1], now=110)
    assert not result.valid and result.envelope is None


def test_reordering_is_rejected_at_source_boundary():
    xs=list(receipts()); xs[1],xs[2]=xs[2],xs[1]
    assert not SourceNativeEnvelopeAssembler().assemble(xs, now=110).valid


def test_identity_substitution_is_rejected():
    xs=list(receipts()); xs[3]=DecisionReceipt.issue(stage="canary", action_identity="other", issued_at=103, payload={})
    assert not SourceNativeEnvelopeAssembler().assemble(xs, now=110).valid


def test_tampered_source_payload_is_rejected_before_envelope_build():
    xs=list(receipts()); xs[4]=dataclasses.replace(xs[4], payload={"stage":"evidence","approved":False})
    assert not SourceNativeEnvelopeAssembler().assemble(xs, now=110).valid


def test_non_monotonic_source_chronology_is_rejected():
    xs=list(receipts()); xs[3]=DecisionReceipt.issue(stage="canary", action_identity="act-1", issued_at=50, payload={})
    assert not SourceNativeEnvelopeAssembler().assemble(xs, now=110).valid


def test_future_source_receipt_is_rejected():
    xs=list(receipts()); xs[-1]=DecisionReceipt.issue(stage="attribution", action_identity="act-1", issued_at=999, payload={})
    assert not SourceNativeEnvelopeAssembler().assemble(xs, now=110).valid


def test_receipt_hash_is_bound_inside_evidence_binding():
    r=receipts()[0]; b=r.to_binding()
    assert b.payload["source_receipt_hash"] == r.receipt_hash
    assert b.verify_integrity()


def test_receipt_and_assembler_have_no_mutation_authority():
    forbidden={"execute","mutate","promote","rollback","acquire","release"}
    assert not forbidden.intersection(dir(DecisionReceipt))
    assert not forbidden.intersection(dir(SourceNativeEnvelopeAssembler))
