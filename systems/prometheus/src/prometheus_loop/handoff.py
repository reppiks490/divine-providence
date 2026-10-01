"""Read-only PROMETHEUS -> ASCENSION runtime handoff export.

This module serializes exact PROMETHEUS runtime provenance plus an already
recorded external-attestation/verification-receipt pair into the structural
shape consumed by ASCENSION's Sibling Manifest Conformance Kit v0.1.

It deliberately does not create trust policy, signatures, transparency proofs,
authentication, Transfer, promotion, broker authority, or production authority.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from .attestation import (
    AttestationVerificationReceipt,
    ExternalExecutionAttestation,
    PluginAttestationPolicy,
    validate_external_attestation_binding,
)
from .ids import canonical_json, content_id
from .memory.store import ResearchMemory


EXPORT_VERSION = "0.1"
SIBLING_ID = "PROMETHEUS"

# Descriptive ownership/coordination metadata only. This grants no authority.
_PROMETHEUS_MANIFEST = {
    "system_id": SIBLING_ID,
    "owned_domains": [
        "research_orchestration",
        "research_provenance",
        "plugin_execution_evidence",
    ],
    "mutation_rights": ["own_append_only_research_memory"],
    "interfaces": [
        {
            "name": "research-provenance",
            "version": "0.5",
            "required_inputs": ["plugin_evidence"],
            "emitted_outputs": ["research_provenance_manifest"],
            "assumptions": ["external_verifier_receipt"],
            "invariants": [
                "research_only",
                "production_authorized_false",
                "no_sibling_runtime_mutation",
            ],
        }
    ],
    "requires": ["external_attestation_receipt"],
    "forbids": [
        "production_authority",
        "broker_execution",
        "sibling_runtime_mutation",
    ],
    "shared_state": [],
    "coordination_contracts": [
        "DAEDALUS_review_boundary",
        "NEXUS_contract_identity_when_nexus_backed",
    ],
}


def _record_payload(
    memory: ResearchMemory,
    artifact_id: str,
    expected_type: str,
) -> dict[str, Any]:
    try:
        record = memory.find_by_id(artifact_id)
    except KeyError as exc:
        raise ValueError(f"missing runtime artifact {artifact_id}") from exc
    if record.get("artifact_type") != expected_type:
        raise ValueError(
            f"wrong artifact type for {artifact_id}: expected {expected_type}"
        )
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise ValueError(f"runtime artifact payload is not a mapping for {artifact_id}")
    expected_sha = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    if record.get("content_sha256") != expected_sha:
        raise ValueError(f"runtime artifact content hash mismatch for {artifact_id}")
    return payload


def _attestation_from_payload(payload: dict[str, Any]) -> ExternalExecutionAttestation:
    return ExternalExecutionAttestation(
        plugin_evidence_id=payload["plugin_evidence_id"],
        subject_sha256=payload["subject_sha256"],
        predicate_type=payload["predicate_type"],
        envelope_ref=payload["envelope_ref"],
        envelope_sha256=payload["envelope_sha256"],
        verification_material_sha256=payload["verification_material_sha256"],
        signer_identity=payload["signer_identity"],
        attestation_format=payload["attestation_format"],
    )


def _receipt_from_payload(payload: dict[str, Any]) -> AttestationVerificationReceipt:
    raw_checks = payload.get("checks", ())
    if not isinstance(raw_checks, (list, tuple)):
        raise ValueError("verification receipt checks must be a sequence")
    checks: list[tuple[str, bool]] = []
    for row in raw_checks:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise ValueError("verification receipt check shape is invalid")
        checks.append((row[0], row[1]))
    return AttestationVerificationReceipt(
        attestation_id=payload["attestation_id"],
        verifier_id=payload["verifier_id"],
        trusted_root_id=payload["trusted_root_id"],
        verification_policy_id=payload["verification_policy_id"],
        checks=tuple(checks),
        external_verification_ref=payload["external_verification_ref"],
    )


def build_ascension_handoff_export(
    memory: ResearchMemory,
    *,
    provenance_manifest_id: str,
    plugin_evidence_id: str,
) -> dict[str, Any]:
    """Build one exact, structural ASCENSION handoff export.

    One export corresponds to one strict-attested plugin-evidence item from a
    concrete ResearchProvenanceManifest. The result intentionally omits
    adapter_v0_4_evidence because PROMETHEUS does not own ASCENSION trust
    policy, transparency witnesses, collision verdicts, or signing authority.

    A successful return therefore closes only the runtime-manifest / exact-byte
    / attestation-descriptor transport gap. It must remain
    STRUCTURALLY_CONFORMANT rather than ADAPTER_READY_UNVERIFIED until the
    separately governed ASCENSION evidence is supplied and verified.
    """

    manifest = memory.reconstruct_provenance_manifest(provenance_manifest_id)
    if manifest.plugin_attestation_policy is not PluginAttestationPolicy.REQUIRE_VERIFIED:
        raise ValueError("ASCENSION handoff requires REQUIRE_VERIFIED provenance")
    if plugin_evidence_id not in manifest.plugin_evidence_ids:
        raise ValueError("plugin evidence is not bound to provenance manifest")

    evidence_payload = _record_payload(
        memory, plugin_evidence_id, "PluginExecutionEvidence"
    )
    if content_id("plugin-evidence", evidence_payload) != plugin_evidence_id:
        raise ValueError("plugin evidence content id mismatch")

    matching_attestations: list[
        tuple[str, ExternalExecutionAttestation, dict[str, Any]]
    ] = []
    for attestation_id in manifest.external_attestation_ids:
        payload = _record_payload(
            memory, attestation_id, "ExternalExecutionAttestation"
        )
        attestation = _attestation_from_payload(payload)
        if attestation.artifact_id != attestation_id:
            raise ValueError("external attestation content id mismatch")
        if attestation.plugin_evidence_id == plugin_evidence_id:
            matching_attestations.append((attestation_id, attestation, payload))
    if len(matching_attestations) != 1:
        raise ValueError(
            "provenance manifest must bind exactly one attestation for plugin evidence"
        )
    attestation_id, attestation, attestation_payload = matching_attestations[0]

    matching_receipts: list[
        tuple[str, AttestationVerificationReceipt, dict[str, Any]]
    ] = []
    for receipt_id in manifest.attestation_verification_ids:
        payload = _record_payload(
            memory, receipt_id, "AttestationVerificationReceipt"
        )
        receipt = _receipt_from_payload(payload)
        if receipt.artifact_id != receipt_id:
            raise ValueError("attestation verification content id mismatch")
        if receipt.attestation_id == attestation_id:
            matching_receipts.append((receipt_id, receipt, payload))
    if len(matching_receipts) != 1:
        raise ValueError(
            "provenance manifest must bind exactly one verification receipt for attestation"
        )
    receipt_id, receipt, receipt_payload = matching_receipts[0]

    validate_external_attestation_binding(
        plugin_evidence_id, attestation, receipt
    )
    if not receipt.verified:
        raise ValueError("external attestation verification receipt is not verified")

    manifest_record = memory.find_by_id(provenance_manifest_id)
    manifest_payload = manifest_record["payload"]
    manifest_bytes = canonical_json(manifest_payload).encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_record.get("content_sha256") != manifest_sha256:
        raise ValueError("provenance manifest content hash mismatch")

    authority_attestation = dict(attestation_payload)
    authority_attestation["artifact_id"] = attestation_id

    return {
        "export_version": EXPORT_VERSION,
        "sibling_id": SIBLING_ID,
        "manifest": {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in _PROMETHEUS_MANIFEST.items()
        },
        "artifact": {
            "sha256": manifest_sha256,
            "content_ref": f"research-memory://{provenance_manifest_id}",
            "content_b64": base64.b64encode(manifest_bytes).decode("ascii"),
        },
        "authority": {
            "owner_system": SIBLING_ID,
            "attestation": authority_attestation,
            "verification_receipt": dict(receipt_payload),
        },
        "extensions": {
            "prometheus": {
                "provenance_manifest_id": provenance_manifest_id,
                "plugin_evidence_id": plugin_evidence_id,
                "external_attestation_id": attestation_id,
                "attestation_verification_id": receipt_id,
                "plugin_attestation_policy": manifest.plugin_attestation_policy.value,
                "source_contract_ids": list(manifest.source_contract_ids),
                "parent_manifest_ids": list(manifest.parent_manifest_ids),
                "authenticated": False,
                "transfer_verified": False,
                "production_authorized": False,
            }
        },
    }
