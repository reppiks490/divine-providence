import dataclasses
from proof_envelope import EvidenceBinding, ProofEnvelope, ProofEnvelopeBuilder, ProofEnvelopeVerifier


def binding(kind, payload, identity='svc|restart|x'):
    return EvidenceBinding.create(kind=kind, action_identity=identity, payload=payload)


def complete():
    parts = [
        binding('guard', {'approved': True, 'reason': 'approved'}),
        binding('topology', {'approved': True, 'lease_scopes': ['component:svc']}),
        binding('lease', {'owner': 'cycle:1:x', 'scopes': ['component:svc']}),
        binding('canary', {'status': 'promoted', 'proof_hash': 'abc'}),
        binding('evidence', {'evidence_hash': 'def', 'component': 'svc'}),
        binding('attribution', {'evidence_hash': 'ghi', 'eligible': True}),
    ]
    return ProofEnvelopeBuilder().build(parts)


def test_complete_envelope_verifies():
    env = complete()
    result = ProofEnvelopeVerifier().verify(env)
    assert result.valid
    assert result.reason == 'proof envelope verified'


def test_payload_tamper_is_detected():
    env = complete()
    bad_first = dataclasses.replace(env.bindings[0], payload={'approved': False})
    bad = dataclasses.replace(env, bindings=(bad_first,) + env.bindings[1:])
    assert not ProofEnvelopeVerifier().verify(bad).valid


def test_omitted_required_stage_is_detected_even_if_rehashed():
    env = complete()
    rebuilt = ProofEnvelopeBuilder().build([b for b in env.bindings if b.kind != 'lease'])
    result = ProofEnvelopeVerifier().verify(rebuilt)
    assert not result.valid
    assert 'required proof stages' in result.reason


def test_reordering_is_detected_even_if_rehashed():
    env = complete()
    parts = list(env.bindings)
    parts[1], parts[2] = parts[2], parts[1]
    rebuilt = ProofEnvelopeBuilder().build(parts)
    result = ProofEnvelopeVerifier().verify(rebuilt)
    assert not result.valid
    assert 'stage order' in result.reason


def test_action_identity_substitution_is_detected():
    env = complete()
    parts = list(env.bindings)
    parts[-1] = binding('attribution', {'evidence_hash': 'ghi', 'eligible': True}, identity='other|restart|x')
    rebuilt = ProofEnvelopeBuilder().build(parts)
    result = ProofEnvelopeVerifier().verify(rebuilt)
    assert not result.valid
    assert 'action identity mismatch' in result.reason


def test_duplicate_stage_is_rejected():
    env = complete()
    parts = list(env.bindings)
    parts.insert(2, binding('topology', {'approved': True}))
    rebuilt = ProofEnvelopeBuilder().build(parts)
    result = ProofEnvelopeVerifier().verify(rebuilt)
    assert not result.valid
    assert 'duplicate proof stage' in result.reason


def test_envelope_hash_tamper_is_detected():
    env = complete()
    bad = dataclasses.replace(env, envelope_hash='0' * 64)
    assert not ProofEnvelopeVerifier().verify(bad).valid


def test_binding_hash_is_canonical_for_mapping_key_order():
    a = binding('guard', {'approved': True, 'reason': 'x'})
    b = binding('guard', {'reason': 'x', 'approved': True})
    assert a.binding_hash == b.binding_hash


def test_verifier_is_pure_and_has_no_execution_authority():
    verifier = ProofEnvelopeVerifier()
    for forbidden in ('execute', 'mutate', 'promote', 'rollback', 'acquire'):
        assert not hasattr(verifier, forbidden)


def test_stale_envelope_is_rejected():
    env = ProofEnvelopeBuilder().build(list(complete().bindings), now=100.0, ttl_seconds=10.0)
    result = ProofEnvelopeVerifier().verify(env, now=111.0)
    assert not result.valid
    assert 'stale' in result.reason


def test_future_envelope_is_rejected():
    env = ProofEnvelopeBuilder().build(list(complete().bindings), now=100.0, ttl_seconds=10.0)
    result = ProofEnvelopeVerifier().verify(env, now=99.0)
    assert not result.valid
    assert 'not yet valid' in result.reason
