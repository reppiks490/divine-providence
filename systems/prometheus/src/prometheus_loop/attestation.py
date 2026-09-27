from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .ids import content_id

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_CHECKS = frozenset({"signature", "subject_digest", "signer_identity", "trusted_root"})


class PluginAttestationPolicy(str, Enum):
    OPTIONAL = "OPTIONAL"
    REQUIRE_VERIFIED = "REQUIRE_VERIFIED"


def _require_non_empty(name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{name} must be non-empty")


def _require_sha256(name: str, value: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase sha256 digest")


@dataclass(frozen=True)
class ExternalExecutionAttestation:
    plugin_evidence_id: str
    subject_sha256: str
    predicate_type: str
    envelope_ref: str
    envelope_sha256: str
    verification_material_sha256: str
    signer_identity: str
    attestation_format: str

    def __post_init__(self) -> None:
        if not self.plugin_evidence_id.startswith("plugin-evidence:"):
            raise ValueError("plugin_evidence_id must use the plugin-evidence: namespace")
        evidence_digest = self.plugin_evidence_id.removeprefix("plugin-evidence:")
        _require_sha256("plugin_evidence_id digest", evidence_digest)
        _require_sha256("subject_sha256", self.subject_sha256)
        if self.subject_sha256 != evidence_digest:
            raise ValueError("attestation subject digest must match plugin evidence digest")
        _require_sha256("envelope_sha256", self.envelope_sha256)
        _require_sha256("verification_material_sha256", self.verification_material_sha256)
        for name in ("predicate_type", "envelope_ref", "signer_identity", "attestation_format"):
            _require_non_empty(name, getattr(self, name))

    @property
    def artifact_id(self) -> str:
        return content_id("external-attestation", self)


@dataclass(frozen=True)
class AttestationVerificationReceipt:
    attestation_id: str
    verifier_id: str
    trusted_root_id: str
    verification_policy_id: str
    checks: tuple[tuple[str, bool], ...]
    external_verification_ref: str

    def __post_init__(self) -> None:
        if not self.attestation_id.startswith("external-attestation:"):
            raise ValueError("attestation_id must use the external-attestation: namespace")
        for name in ("verifier_id", "trusted_root_id", "verification_policy_id", "external_verification_ref"):
            _require_non_empty(name, getattr(self, name))
        names = [name for name, _ in self.checks]
        if any(not name for name in names):
            raise ValueError("verification check name must be non-empty")
        if len(set(names)) != len(names):
            raise ValueError("duplicate verification check name")
        if any(not isinstance(passed, bool) for _, passed in self.checks):
            raise ValueError("verification check result must be boolean")
        object.__setattr__(self, "checks", tuple(sorted(self.checks, key=lambda item: item[0])))

    @property
    def verified(self) -> bool:
        values = dict(self.checks)
        return all(values.get(name) is True for name in _REQUIRED_CHECKS)

    @property
    def artifact_id(self) -> str:
        return content_id("attestation-verification", self)


def validate_external_attestation_binding(
    plugin_evidence_id: str,
    attestation: ExternalExecutionAttestation,
    receipt: AttestationVerificationReceipt,
) -> None:
    if attestation.plugin_evidence_id != plugin_evidence_id:
        raise ValueError("external attestation plugin evidence mismatch")
    expected_digest = plugin_evidence_id.removeprefix("plugin-evidence:")
    if attestation.subject_sha256 != expected_digest:
        raise ValueError("external attestation subject digest mismatch")
    if receipt.attestation_id != attestation.artifact_id:
        raise ValueError("attestation verification receipt does not match attestation")
