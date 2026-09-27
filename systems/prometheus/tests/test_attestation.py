import pytest

from prometheus_loop.attestation import (
    AttestationVerificationReceipt,
    ExternalExecutionAttestation,
    PluginAttestationPolicy,
    validate_external_attestation_binding,
)


EVIDENCE_DIGEST = "a" * 64
EVIDENCE_ID = f"plugin-evidence:{EVIDENCE_DIGEST}"


def _attestation(**overrides):
    values = dict(
        plugin_evidence_id=EVIDENCE_ID,
        subject_sha256=EVIDENCE_DIGEST,
        predicate_type="https://example.invalid/predicate/plugin-execution/v1",
        envelope_ref="store://attestations/envelope-1",
        envelope_sha256="b" * 64,
        verification_material_sha256="c" * 64,
        signer_identity="host://plugin-runner/fixture",
        attestation_format="application/vnd.in-toto+json",
    )
    values.update(overrides)
    return ExternalExecutionAttestation(**values)


def _receipt(attestation=None, **overrides):
    attestation = attestation or _attestation()
    values = dict(
        attestation_id=attestation.artifact_id,
        verifier_id="verifier://fixture/v1",
        trusted_root_id="trust-root://fixture/v1",
        verification_policy_id="policy://plugin-execution/v1",
        checks=(
            ("trusted_root", True),
            ("signature", True),
            ("subject_digest", True),
            ("signer_identity", True),
        ),
        external_verification_ref="store://verification/receipt-1",
    )
    values.update(overrides)
    return AttestationVerificationReceipt(**values)


def test_attestation_is_content_addressed_and_canonical():
    first = _attestation()
    second = _attestation()
    assert first == second
    assert first.artifact_id == second.artifact_id
    assert first.artifact_id.startswith("external-attestation:")


def test_attestation_subject_must_match_plugin_evidence_digest():
    with pytest.raises(ValueError, match="subject digest"):
        _attestation(subject_sha256="d" * 64)


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("plugin_evidence_id", "candidate:" + "a" * 64, "plugin-evidence"),
        ("subject_sha256", "A" * 64, "sha256"),
        ("envelope_sha256", "abc", "sha256"),
        ("verification_material_sha256", "g" * 64, "sha256"),
        ("predicate_type", "", "predicate_type"),
        ("envelope_ref", "", "envelope_ref"),
        ("signer_identity", "", "signer_identity"),
        ("attestation_format", "", "attestation_format"),
    ],
)
def test_attestation_rejects_malformed_fields(field, value, error):
    with pytest.raises(ValueError, match=error):
        _attestation(**{field: value})


def test_receipt_canonicalizes_checks_and_requires_unique_names():
    receipt = _receipt()
    assert receipt.checks == (
        ("signature", True),
        ("signer_identity", True),
        ("subject_digest", True),
        ("trusted_root", True),
    )
    assert receipt.verified is True
    assert receipt.artifact_id.startswith("attestation-verification:")

    with pytest.raises(ValueError, match="duplicate.*check"):
        _receipt(checks=(("signature", True), ("signature", True)))


def test_receipt_is_unverified_when_mandatory_check_is_missing_or_false():
    missing = _receipt(checks=(("signature", True), ("subject_digest", True), ("signer_identity", True)))
    assert missing.verified is False

    failed = _receipt(
        checks=(
            ("signature", False),
            ("subject_digest", True),
            ("signer_identity", True),
            ("trusted_root", True),
        )
    )
    assert failed.verified is False


def test_receipt_rejects_wrong_namespace_and_empty_trust_identity():
    with pytest.raises(ValueError, match="external-attestation"):
        _receipt(attestation_id="plugin-evidence:" + "a" * 64)
    with pytest.raises(ValueError, match="verifier_id"):
        _receipt(verifier_id="")
    with pytest.raises(ValueError, match="trusted_root_id"):
        _receipt(trusted_root_id="")
    with pytest.raises(ValueError, match="verification_policy_id"):
        _receipt(verification_policy_id="")
    with pytest.raises(ValueError, match="external_verification_ref"):
        _receipt(external_verification_ref="")


def test_binding_validator_rejects_cross_plugin_attestation_or_receipt():
    attestation = _attestation()
    receipt = _receipt(attestation)
    validate_external_attestation_binding(EVIDENCE_ID, attestation, receipt)

    with pytest.raises(ValueError, match="plugin evidence"):
        validate_external_attestation_binding("plugin-evidence:" + "d" * 64, attestation, receipt)

    other = _attestation(envelope_ref="store://attestations/other")
    with pytest.raises(ValueError, match="receipt.*attestation"):
        validate_external_attestation_binding(EVIDENCE_ID, attestation, _receipt(other))


def test_policy_modes_are_explicit_and_optional_is_default_candidate():
    assert tuple(PluginAttestationPolicy) == (
        PluginAttestationPolicy.OPTIONAL,
        PluginAttestationPolicy.REQUIRE_VERIFIED,
    )
