"""ASCENSION Sibling Manifest Conformance Kit v0.1.

Read-only structural conformance tooling. It DOES NOT authenticate, sign, confer
authority, or establish Transfer. It only determines whether a sibling export is
structurally ready to be handed to the separately governed Adapter v0.4 trust
and transparency verification chain.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from typing import Any, Mapping

KIT_VERSION = "0.1"
PROFILE_ID = "ascension-adapter-v0.4-transfer-profile"
STATUS_NONCONFORMANT = "NONCONFORMANT"
STATUS_STRUCTURAL = "STRUCTURALLY_CONFORMANT"
STATUS_ADAPTER_READY = "ADAPTER_READY_UNVERIFIED"

MANIFEST_REQUIRED = (
    "system_id", "owned_domains", "mutation_rights", "interfaces", "requires",
    "forbids", "shared_state", "coordination_contracts",
)
ATTESTATION_REQUIRED = (
    "plugin_evidence_id", "subject_sha256", "predicate_type", "envelope_ref",
    "envelope_sha256", "verification_material_sha256", "signer_identity",
    "attestation_format", "artifact_id",
)
RECEIPT_REQUIRED = (
    "attestation_id", "verifier_id", "trusted_root_id", "verification_policy_id",
    "checks", "external_verification_ref",
)
MANDATORY_RECEIPT_CHECKS = ("signature", "subject_digest", "signer_identity", "trusted_root")
ADAPTER_BACKENDS = {
    "adapter": "manifest-trust-collision-adapter-v0.4",
    "trust": "evaluator-fabric-attestation-v0.4",
    "inclusion": "evaluator-fabric-inclusion-v0.8-strict-rfc9162",
    "transition": "evaluator-fabric-transition-v0.7-compact-witness",
    "transparency": "evaluator-fabric-transparency-v0.8-strict-inclusion+v0.7-compact-witness",
    "collision": "collision-detector-v0.3",
    "inclusion_schema": "rfc9162-index-bound-hash-path-v0.8",
    "hash_algorithm": "SHA-256",
    "witness_algorithm": "Ed25519",
}
ADAPTER_DEPENDENCY_SHA256 = {
    "trust": "b189d3c21516ee62ee15da764f9bbedd0c036d180a4cb316d81c2426717d238e",
    "inclusion": "8c40d16061bbc436cf78d3029f6b4d04b507dad8779e3dba74fd6ce51746de4b",
    "transition": "eb8b4ad9990f8b57530aa88415827a762c6b1ff136996a33fe158ea8a72c33b6",
    "collision": "fda90e02b3774219d0b52640e58f35510f5834c1065a2729cb563f1b303f5abb",
}
TARGET_ADAPTER_PACKAGE_SHA256 = "0145bf2ecb3ecd606c9d70b26b671ce397bba17f35dc56da4c691997bbd8e224"
ALLOWED_TOP_LEVEL = {
    "export_version", "sibling_id", "manifest", "artifact", "authority",
    "adapter_v0_4_evidence", "extensions",
}
FORBIDDEN_SECRET_NAMES = {
    "private_key", "privatekey", "secret_key", "secretkey", "password", "passwd",
    "bearer_token", "access_token", "refresh_token", "api_key", "apikey", "cookie",
    "client_secret", "credential", "credentials",
}


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _json_safe(value: Any):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"$bytes_hex": bytes(value).hex()}
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("unsupported evidence type")

def _stable_sha(value: Any) -> str:
    data = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _scan_secret_fields(value: Any, reasons: list[str]) -> None:
    if isinstance(value, Mapping):
        for k, v in value.items():
            key = str(k).lower()
            if key in FORBIDDEN_SECRET_NAMES:
                reasons.append("forbidden_secret_field:" + key)
            _scan_secret_fields(v, reasons)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _scan_secret_fields(v, reasons)


def _validate_manifest(m: Any, sibling_id: str, reasons: list[str]) -> None:
    if not isinstance(m, Mapping):
        reasons.append("manifest_invalid")
        return
    missing = [k for k in MANIFEST_REQUIRED if k not in m]
    if missing:
        reasons.append("manifest_schema_incomplete:" + ",".join(sorted(missing)))
    if m.get("system_id") != sibling_id:
        reasons.append("manifest_system_id_mismatch")
    for k in ("owned_domains", "mutation_rights", "interfaces", "requires", "forbids", "shared_state", "coordination_contracts"):
        if k in m and not isinstance(m.get(k), list):
            reasons.append("manifest_field_type_invalid:" + k)


def _validate_artifact(a: Any, reasons: list[str]) -> tuple[bool, bool]:
    """Return (descriptor_ok, bytes_present_and_bound)."""
    if not isinstance(a, Mapping):
        reasons.append("artifact_descriptor_invalid")
        return False, False
    digest = a.get("sha256")
    if not _is_sha256(digest):
        reasons.append("artifact_sha256_invalid")
    if not _nonempty(a.get("content_ref")):
        reasons.append("artifact_content_ref_invalid")
    has_bytes = "content_b64" in a
    bound = False
    if has_bytes:
        try:
            raw = base64.b64decode(a.get("content_b64"), validate=True)
            bound = _is_sha256(digest) and hashlib.sha256(raw).hexdigest() == digest
            if not bound:
                reasons.append("artifact_content_digest_mismatch")
        except Exception:
            reasons.append("artifact_content_b64_invalid")
    return not any(r.startswith("artifact_") for r in reasons), bool(has_bytes and bound)


def _validate_authority(authority: Any, sibling_id: str, reasons: list[str]) -> bool:
    if not isinstance(authority, Mapping):
        reasons.append("authority_descriptor_invalid")
        return False
    if authority.get("owner_system") != sibling_id:
        reasons.append("authority_owner_mismatch")
    att = authority.get("attestation")
    receipt = authority.get("verification_receipt")
    if not isinstance(att, Mapping):
        reasons.append("attestation_descriptor_invalid")
        return False
    missing = [k for k in ATTESTATION_REQUIRED if k not in att]
    if missing:
        reasons.append("attestation_descriptor_incomplete:" + ",".join(sorted(missing)))
    for field in ("subject_sha256", "envelope_sha256", "verification_material_sha256"):
        if field in att and not _is_sha256(att.get(field)):
            reasons.append("attestation_digest_invalid:" + field)
    for field in ("predicate_type", "envelope_ref", "signer_identity", "attestation_format", "artifact_id", "plugin_evidence_id"):
        if field in att and not _nonempty(att.get(field)):
            reasons.append("attestation_field_invalid:" + field)
    pid = att.get("plugin_evidence_id")
    subj = att.get("subject_sha256")
    if isinstance(pid, str) and isinstance(subj, str):
        if not pid.startswith("plugin-evidence:") or pid.split(":", 1)[-1] != subj:
            reasons.append("attestation_plugin_evidence_binding_mismatch")
    if isinstance(pid, str) and pid.startswith("plugin-evidence:") and isinstance(subj, str):
        suffix = pid.split(":", 1)[1]
        if suffix != subj:
            reasons.append("attestation_subject_digest_mismatch")
    # Explicitly preserve a separate reason when the subject digest itself has
    # been substituted even if the plugin-evidence binding also fails.
    if isinstance(pid, str) and pid.startswith("plugin-evidence:") and isinstance(subj, str) and pid.split(":",1)[1] != subj:
        reasons.append("attestation_subject_digest_mismatch")

    if not isinstance(receipt, Mapping):
        reasons.append("verification_receipt_invalid")
        return False
    missing = [k for k in RECEIPT_REQUIRED if k not in receipt]
    if missing:
        reasons.append("verification_receipt_incomplete:" + ",".join(sorted(missing)))
    for field in ("attestation_id", "verifier_id", "trusted_root_id", "verification_policy_id", "external_verification_ref"):
        if field in receipt and not _nonempty(receipt.get(field)):
            reasons.append("verification_receipt_field_invalid:" + field)
    if isinstance(att, Mapping) and receipt.get("attestation_id") != att.get("artifact_id"):
        reasons.append("receipt_attestation_id_mismatch")

    checks = receipt.get("checks")
    seen: dict[str, bool] = {}
    if not isinstance(checks, list):
        reasons.append("verification_receipt_checks_invalid")
    else:
        for item in checks:
            if not (isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[0], str) and isinstance(item[1], bool)):
                reasons.append("verification_receipt_check_invalid")
                continue
            name, passed = item
            if name in seen:
                reasons.append("verification_receipt_duplicate_check:" + name)
            else:
                seen[name] = passed
        for name in MANDATORY_RECEIPT_CHECKS:
            if name not in seen:
                reasons.append("verification_receipt_missing_check:" + name)
            elif not seen[name]:
                reasons.append("verification_receipt_failed_check:" + name)
    return not any(r.startswith(("authority_", "attestation_", "verification_receipt_", "receipt_")) for r in reasons)


def _validate_adapter_evidence(e: Any, reasons: list[str]) -> bool:
    """Validate Adapter v0.4 input shape only; never authenticate evidence."""
    if e is None:
        return False
    if not isinstance(e, Mapping):
        reasons.append("adapter_evidence_invalid")
        return False
    required = ("prior_collision_report", "trust_policy", "attestations", "transparency_evidence", "backend_contract")
    if any(k not in e for k in required):
        reasons.append("adapter_evidence_incomplete")
        return False

    prior = e.get("prior_collision_report")
    prior_required = {"detector", "version", "collision_free", "findings", "boundary_gate", "non_interference_gate"}
    if not isinstance(prior, Mapping) or not prior_required.issubset(prior):
        reasons.append("adapter_prior_collision_report_incomplete")
    elif prior.get("boundary_gate") is not True or prior.get("non_interference_gate") is not True:
        reasons.append("adapter_prior_collision_gate_failed")

    policy = e.get("trust_policy")
    trust_required = {"policy_version", "minimum_policy_version", "allowed_algorithms", "signers", "thresholds", "transparency_policy"}
    if not isinstance(policy, Mapping) or not trust_required.issubset(policy):
        reasons.append("adapter_trust_policy_incomplete")
        tp = None
    else:
        if not isinstance(policy.get("signers"), Mapping) or not policy.get("signers"):
            reasons.append("adapter_trust_signers_missing")
        if not isinstance(policy.get("thresholds"), Mapping) or not policy.get("thresholds"):
            reasons.append("adapter_trust_thresholds_missing")
        if not isinstance(policy.get("allowed_algorithms"), list) or "Ed25519" not in policy.get("allowed_algorithms", []):
            reasons.append("adapter_trust_algorithm_missing")
        tp = policy.get("transparency_policy")
    tp_required = {"required", "hash_algorithm", "witness_algorithm", "log_id", "trusted_checkpoint", "witness_keys", "minimum_witnesses", "max_witness_age_seconds", "future_tolerance_seconds"}
    if not isinstance(tp, Mapping) or not tp_required.issubset(tp):
        reasons.append("adapter_transparency_policy_incomplete")
    else:
        if tp.get("required") is not True or tp.get("hash_algorithm") != "SHA-256" or tp.get("witness_algorithm") != "Ed25519":
            reasons.append("adapter_transparency_policy_incompatible")
        if not isinstance(tp.get("witness_keys"), Mapping) or not tp.get("witness_keys"):
            reasons.append("adapter_witness_keys_missing")
        cp=tp.get("trusted_checkpoint")
        if not isinstance(cp, Mapping) or type(cp.get("tree_size")) is not int or cp.get("tree_size",0) < 1 or not _is_sha256(cp.get("root_hash")):
            reasons.append("adapter_trusted_checkpoint_invalid")

    ats = e.get("attestations")
    att_payload_required={"algorithm","signer_id","subject","issued_at","policy_version","evidence_class","manifest_sha256","artifact_sha256","collision_report_sha256"}
    if not isinstance(ats, list) or not ats:
        reasons.append("adapter_attestations_missing")
    else:
        for att in ats:
            if not isinstance(att, Mapping) or not isinstance(att.get("payload"), Mapping) or not att_payload_required.issubset(att.get("payload",{})) or not _nonempty(att.get("signature_hex")):
                reasons.append("adapter_attestation_shape_invalid")
                break

    tr = e.get("transparency_evidence")
    if not isinstance(tr, Mapping) or not isinstance(tr.get("inclusion"), Mapping) or not isinstance(tr.get("transition"), Mapping):
        reasons.append("adapter_transparency_evidence_incomplete")
    else:
        inc=tr["inclusion"]; transition=tr["transition"]
        if not {"leaf_index","tree_size","root_hash","path"}.issubset(inc):
            reasons.append("adapter_inclusion_evidence_incomplete")
        if not {"first_size","second_size","first_root_hash","second_root_hash","consistency_path","witness_observations"}.issubset(transition):
            reasons.append("adapter_transition_evidence_incomplete")
        elif not isinstance(transition.get("witness_observations"), list):
            reasons.append("adapter_transition_evidence_incomplete")

    bc = e.get("backend_contract")
    full_bc_required=set(ADAPTER_BACKENDS) | {"backend_artifact_sha256", "transparency_policy_sha256"}
    if not isinstance(bc, Mapping):
        reasons.append("adapter_backend_contract_invalid")
    else:
        if not full_bc_required.issubset(bc):
            reasons.append("adapter_backend_contract_incomplete")
        for key, expected in ADAPTER_BACKENDS.items():
            if bc.get(key) != expected:
                reasons.append("adapter_backend_mismatch:" + key)
        deps=bc.get("backend_artifact_sha256")
        if not isinstance(deps, Mapping):
            reasons.append("adapter_backend_artifact_digests_invalid")
        else:
            for key, expected in ADAPTER_DEPENDENCY_SHA256.items():
                if deps.get(key) != expected:
                    reasons.append("adapter_backend_artifact_digest_mismatch:" + key)
        if not _is_sha256(bc.get("transparency_policy_sha256")):
            reasons.append("adapter_transparency_policy_digest_invalid")
        elif isinstance(tp, Mapping) and bc.get("transparency_policy_sha256") != _stable_sha(tp):
            reasons.append("adapter_transparency_policy_digest_mismatch")

    return not any(r.startswith("adapter_") for r in reasons)


def validate_export(export: Any) -> dict[str, Any]:
    """Validate a sibling handoff export without conferring authenticity.

    `ready_for_adapter_v0_4` means only that the documented Adapter v0.4 input
    material is structurally present. Cryptographic verification must still be
    performed by the Adapter/Evaluator chain under an external trust policy.
    """
    try:
        x = copy.deepcopy(dict(export)) if isinstance(export, Mapping) else None
    except Exception:
        x = None
    reasons: list[str] = []
    warnings = ["cryptographic_authenticity_not_established", "transfer_not_verified"]
    if x is None:
        return {"conformant": False, "ready_for_adapter_v0_4": False, "authenticated": False, "status": STATUS_NONCONFORMANT, "reasons": ["export_invalid"], "warnings": warnings, "digests": {}}

    for key in x:
        if key not in ALLOWED_TOP_LEVEL:
            reasons.append("unrecognized_top_level_field:" + str(key))
    if x.get("export_version") != KIT_VERSION:
        reasons.append("export_version_unsupported")
    sibling_id = x.get("sibling_id")
    if not _nonempty(sibling_id):
        reasons.append("sibling_id_invalid")
        sibling_id = ""

    _scan_secret_fields(x, reasons)
    _validate_manifest(x.get("manifest"), sibling_id, reasons)
    _, artifact_bound = _validate_artifact(x.get("artifact"), reasons)
    _validate_authority(x.get("authority"), sibling_id, reasons)

    # Structural conformance deliberately does not require Adapter material;
    # that distinction is the purpose of the two readiness levels.
    structural_prefixes = (
        "unrecognized_top_level_field:", "export_", "sibling_", "forbidden_secret_field:",
        "manifest_", "artifact_", "authority_", "attestation_", "verification_receipt_", "receipt_",
    )
    structural_reasons_before_adapter = [r for r in reasons if r.startswith(structural_prefixes)]
    evidence = x.get("adapter_v0_4_evidence")
    adapter_shape_ok = _validate_adapter_evidence(evidence, reasons) if evidence is not None else False
    structural_ok = not structural_reasons_before_adapter
    ready = structural_ok and artifact_bound and adapter_shape_ok

    status = STATUS_NONCONFORMANT if not structural_ok else (STATUS_ADAPTER_READY if ready else STATUS_STRUCTURAL)
    manifest_digest = _stable_sha(x.get("manifest")) if isinstance(x.get("manifest"), Mapping) else None
    export_digest = _stable_sha(x)
    return {
        "conformant": structural_ok,
        "ready_for_adapter_v0_4": ready,
        "authenticated": False,
        "status": status,
        "reasons": sorted(set(reasons)),
        "warnings": warnings,
        "digests": {"export_sha256": export_digest, "manifest_descriptor_sha256": manifest_digest},
        "profile_id": PROFILE_ID,
        "kit_version": KIT_VERSION,
    }


def build_handoff_checklist(sibling_id: str) -> dict[str, Any]:
    sid = str(sibling_id)
    return {
        "kit_version": KIT_VERSION,
        "profile_id": PROFILE_ID,
        "sibling_id": sid,
        "grants_authority": False,
        "target_adapter_package_sha256": TARGET_ADAPTER_PACKAGE_SHA256,
        "required_layers": [
            "collision_manifest",
            "artifact_digest_and_transferable_bytes",
            "sibling_attestation_descriptor",
            "external_verification_receipt",
            "adapter_v0_4_prior_collision_report",
            "adapter_v0_4_trust_policy",
            "adapter_v0_4_attestations",
            "adapter_v0_4_transparency_evidence",
            "adapter_v0_4_backend_contract",
        ],
        "mandatory_receipt_checks": list(MANDATORY_RECEIPT_CHECKS),
        "explicit_nonclaims": [
            "conformance_is_not_authentication",
            "receipt_is_not_reverified_by_this_kit",
            "sibling_authority_is_not_created_by_ascension",
            "transfer_is_not_verified_until_adapter_execution",
        ],
    }


def prometheus_v0_5_declared_profile() -> dict[str, Any]:
    """Machine-readable summary of the sibling-owned v0.5 declared contract.

    This is derived from PROMETHEUS's design/checkpoint contract and is not a
    runtime manifest or cryptographic attestation.
    """
    return {
        "profile_id": "prometheus-v0.5-declared-attestation-contract",
        "source_commit": "4746f11d493a1e6ed906da8e8d516e9b0963c276",
        "evidence_class": "DECLARED_CONTRACT",
        "is_runtime_manifest": False,
        "external_attestation_required_fields": [
            "plugin_evidence_id", "subject_sha256", "predicate_type", "envelope_ref",
            "envelope_sha256", "verification_material_sha256", "signer_identity", "attestation_format",
        ],
        "verification_receipt_required_fields": [
            "attestation_id", "verifier_id", "trusted_root_id", "verification_policy_id",
            "checks", "external_verification_ref",
        ],
        "mandatory_receipt_checks": list(MANDATORY_RECEIPT_CHECKS),
        "declared_trust_boundary": "external_verifier_receipt_only",
        "known_gap_to_adapter_v0_4": [
            "raw_runtime_manifest_not_supplied_here",
            "artifact_bytes_not_supplied_here",
            "trust_policy_not_supplied_here",
            "adapter_attestation_set_not_supplied_here",
            "strict_transparency_evidence_not_supplied_here",
            "pinned_backend_contract_not_supplied_here",
        ],
    }
