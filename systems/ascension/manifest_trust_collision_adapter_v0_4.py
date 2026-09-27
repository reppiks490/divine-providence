"""ASCENSION Manifest Trust -> Collision Adapter v0.4.

Read-only CANDIDATE bridge. It composes:
- Evaluator Fabric v0.4 attestation trust
- Evaluator Fabric v0.8 strict RFC 9162 inclusion verification
- Evaluator Fabric v0.7 compact consistency + signed witness observations
- Collision Detector v0.3 semantic/structural collision analysis

It does not establish sibling authority, witness independence, or semantic truth.
"""
from __future__ import annotations

import copy
import hashlib
from datetime import timezone
from pathlib import Path
from typing import Any, Mapping

import evaluator_fabric_v0_4 as _ef4_module
import evaluator_fabric_v0_7 as _ef7_module
import evaluator_fabric_v0_8 as _ef8_module
import collision_detector_v0_3 as _cd3_module
from evaluator_fabric_v0_4 import verify_attestation_set, canonical_json
from evaluator_fabric_v0_8 import merkle_leaf_hash, verify_transparency_evidence
from collision_detector_v0_3 import analyze_ecosystem

ADAPTER_VERSION = "0.4"
ADAPTER_ID = "manifest-trust-collision-adapter-v0.4"
TRUST_BACKEND = "evaluator-fabric-attestation-v0.4"
INCLUSION_BACKEND = "evaluator-fabric-inclusion-v0.8-strict-rfc9162"
TRANSITION_BACKEND = "evaluator-fabric-transition-v0.7-compact-witness"
TRANSPARENCY_BACKEND = "evaluator-fabric-transparency-v0.8-strict-inclusion+v0.7-compact-witness"
COLLISION_BACKEND = "collision-detector-v0.3"
INCLUSION_SCHEMA = "rfc9162-index-bound-hash-path-v0.8"
HASH_ALGORITHM = "SHA-256"
WITNESS_ALGORITHM = "Ed25519"
EXPECTED_DEPENDENCY_SHA256 = {
    "trust": "b189d3c21516ee62ee15da764f9bbedd0c036d180a4cb316d81c2426717d238e",
    "inclusion": "8c40d16061bbc436cf78d3029f6b4d04b507dad8779e3dba74fd6ce51746de4b",
    "transition": "eb8b4ad9990f8b57530aa88415827a762c6b1ff136996a33fe158ea8a72c33b6",
    "collision": "fda90e02b3774219d0b52640e58f35510f5834c1065a2729cb563f1b303f5abb",
}
_DEPENDENCY_MODULES = {
    "trust": _ef4_module,
    "inclusion": _ef8_module,
    "transition": _ef7_module,
    "collision": _cd3_module,
}
REQUIRED = (
    "system_id", "owned_domains", "mutation_rights", "interfaces", "requires",
    "forbids", "shared_state", "coordination_contracts",
)
TRUST_RESULT_REQUIRED = (
    "trusted", "reasons", "valid_signers", "threshold_required", "threshold_role",
    "boundary_gate", "non_interference_gate",
)
PROVENANCE_REQUIRED = (
    "adapter_version", "trust_backend", "inclusion_backend", "transition_backend",
    "transparency_backend", "collision_backend", "inclusion_schema", "valid_signers",
    "threshold_required", "source_subject", "manifest_sha256", "manifest_leaf_hash",
    "artifact_sha256", "transparency_policy_sha256", "backend_contract_sha256",
    "backend_artifact_sha256",
    "trusted_checkpoint", "current_checkpoint", "valid_witnesses", "transparency_mode",
    "attestations_sha256", "prior_collision_report_sha256", "transparency_evidence_sha256",
    "trust_result_sha256", "strict_inclusion_result_sha256", "transition_result_sha256",
)


def _sha_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _json_safe_evidence(value: Any):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"$bytes_hex": bytes(value).hex()}
    if isinstance(value, Mapping):
        return {
            str(k): _json_safe_evidence(v)
            for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe_evidence(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("unsupported evidence type")


def hash_evidence(value: Any) -> str:
    """Deterministic SHA-256 over evidence, including binary proof nodes."""
    return hashlib.sha256(canonical_json(_json_safe_evidence(value))).hexdigest()


def _transparency_policy(trust_policy: Mapping[str, Any] | None):
    if not isinstance(trust_policy, Mapping):
        return None
    tp = trust_policy.get("transparency_policy")
    return copy.deepcopy(dict(tp)) if isinstance(tp, Mapping) else None



def validate_runtime_dependency_integrity():
    """Verify the file-backed backend modules match the build-time pinned bytes."""
    reasons = []
    observed = {}
    for key, module in _DEPENDENCY_MODULES.items():
        try:
            path = Path(module.__file__)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            observed[key] = digest
            if digest != EXPECTED_DEPENDENCY_SHA256[key]:
                reasons.append("runtime_backend_digest_mismatch:" + key)
        except Exception:
            reasons.append("runtime_backend_unreadable:" + key)
    return {
        "valid": not reasons,
        "reasons": sorted(set(reasons)),
        "expected": copy.deepcopy(EXPECTED_DEPENDENCY_SHA256),
        "observed": observed,
    }


def build_backend_contract(trust_policy):
    """Build the exact v0.4 dependency contract for governance pinning.

    Security requires callers to pin this result before any untrusted policy
    mutation; recomputing it after mutation defeats policy-substitution defense.
    """
    tp = _transparency_policy(trust_policy)
    return {
        "adapter": ADAPTER_ID,
        "trust": TRUST_BACKEND,
        "inclusion": INCLUSION_BACKEND,
        "transition": TRANSITION_BACKEND,
        "transparency": TRANSPARENCY_BACKEND,
        "collision": COLLISION_BACKEND,
        "inclusion_schema": INCLUSION_SCHEMA,
        "hash_algorithm": HASH_ALGORITHM,
        "witness_algorithm": WITNESS_ALGORITHM,
        "backend_artifact_sha256": copy.deepcopy(EXPECTED_DEPENDENCY_SHA256),
        "transparency_policy_sha256": _sha_json(tp),
    }


def _validate_backend_contract(backend_contract, trust_policy):
    if not isinstance(backend_contract, Mapping):
        return {
            "valid": False,
            "reasons": ["backend_contract_required"],
            "expected": build_backend_contract(trust_policy),
        }
    supplied = copy.deepcopy(dict(backend_contract))
    expected = build_backend_contract(trust_policy)
    reasons = []
    for key, value in expected.items():
        if key not in supplied:
            reasons.append("backend_contract_missing:" + key)
        elif supplied.get(key) != value:
            if key == "transparency_policy_sha256":
                reasons.append("transparency_policy_digest_mismatch")
            else:
                reasons.append("backend_contract_mismatch:" + key)
    for key in supplied:
        if key not in expected:
            reasons.append("backend_contract_unrecognized:" + str(key))
    return {"valid": not reasons, "reasons": sorted(set(reasons)), "expected": expected}


def validate_trust_result(trust_result):
    reasons = []
    if not isinstance(trust_result, Mapping):
        return {"valid": False, "reasons": ["trust_result_schema_incompatible"]}
    missing = [k for k in TRUST_RESULT_REQUIRED if k not in trust_result]
    if missing:
        reasons.append("trust_result_schema_incompatible")
    else:
        if not isinstance(trust_result.get("trusted"), bool): reasons.append("trust_result_schema_incompatible")
        if not isinstance(trust_result.get("reasons"), list): reasons.append("trust_result_schema_incompatible")
        if not isinstance(trust_result.get("valid_signers"), list): reasons.append("trust_result_schema_incompatible")
        if not isinstance(trust_result.get("boundary_gate"), bool): reasons.append("trust_result_schema_incompatible")
        if not isinstance(trust_result.get("non_interference_gate"), bool): reasons.append("trust_result_schema_incompatible")
        try:
            if int(trust_result.get("threshold_required")) < 1:
                reasons.append("trust_result_schema_incompatible")
        except Exception:
            reasons.append("trust_result_schema_incompatible")
    return {"valid": not reasons, "reasons": sorted(set(reasons))}


def _validate_transparency_policy(tp):
    reasons = []
    if not isinstance(tp, Mapping):
        return {"valid": False, "reasons": ["transparency_policy_required"]}
    required = (
        "required", "hash_algorithm", "witness_algorithm", "log_id", "trusted_checkpoint",
        "witness_keys", "minimum_witnesses", "max_witness_age_seconds", "future_tolerance_seconds",
    )
    if any(k not in tp for k in required): reasons.append("transparency_policy_incomplete")
    if tp.get("required") is not True: reasons.append("transparency_v0_8_required")
    if tp.get("hash_algorithm") != HASH_ALGORITHM: reasons.append("transparency_hash_algorithm_not_allowed")
    if tp.get("witness_algorithm") != WITNESS_ALGORITHM: reasons.append("witness_algorithm_not_allowed")
    if not isinstance(tp.get("log_id"), str) or not tp.get("log_id"): reasons.append("transparency_log_id_invalid")
    if not isinstance(tp.get("witness_keys"), Mapping): reasons.append("witness_keys_invalid")
    cp = tp.get("trusted_checkpoint")
    if not isinstance(cp, Mapping):
        reasons.append("trusted_checkpoint_invalid")
    else:
        try:
            if type(cp.get("tree_size")) is not int or cp.get("tree_size") < 1:
                reasons.append("trusted_checkpoint_invalid")
            root = bytes.fromhex(str(cp.get("root_hash", "")))
            if len(root) != 32: reasons.append("trusted_checkpoint_invalid")
        except Exception:
            reasons.append("trusted_checkpoint_invalid")
    try:
        if type(tp.get("minimum_witnesses")) is not int or tp.get("minimum_witnesses") < 1:
            reasons.append("witness_threshold_invalid")
        if float(tp.get("max_witness_age_seconds")) < 0: reasons.append("witness_time_policy_invalid")
        if float(tp.get("future_tolerance_seconds")) < 0: reasons.append("witness_time_policy_invalid")
    except Exception:
        reasons.append("transparency_policy_numeric_invalid")
    return {"valid": not reasons, "reasons": sorted(set(reasons))}


def _now_iso(now):
    d = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _verify_transparency(manifest, evidence, trust_policy, now):
    tp = _transparency_policy(trust_policy)
    policy_check = _validate_transparency_policy(tp)
    reasons = list(policy_check["reasons"])
    result = {
        "valid": False,
        "reasons": [],
        "mode": TRANSPARENCY_BACKEND,
        "inclusion_backend": INCLUSION_BACKEND,
        "transition_backend": TRANSITION_BACKEND,
        "inclusion_schema": INCLUSION_SCHEMA,
        "manifest_leaf_hash": None,
        "inclusion": None,
        "transition": None,
        "policy_sha256": _sha_json(tp),
    }
    if reasons:
        result["reasons"] = sorted(set(reasons))
        return result
    if not isinstance(evidence, Mapping):
        result["reasons"] = ["transparency_evidence_incomplete"]
        return result
    try:
        inc = copy.deepcopy(dict(evidence["inclusion"]))
        tr = copy.deepcopy(dict(evidence["transition"]))
    except Exception:
        result["reasons"] = ["transparency_evidence_incomplete"]
        return result

    cp = tp["trusted_checkpoint"]
    try:
        if type(tr.get("first_size")) is not int or tr.get("first_size") != cp["tree_size"]:
            reasons.append("trusted_checkpoint_size_mismatch")
        if str(tr.get("first_root_hash")) != str(cp["root_hash"]):
            reasons.append("trusted_checkpoint_root_mismatch")
        if type(inc.get("tree_size")) is not int or type(tr.get("second_size")) is not int or inc.get("tree_size") != tr.get("second_size"):
            reasons.append("inclusion_transition_size_mismatch")
        if str(inc.get("root_hash")) != str(tr.get("second_root_hash")):
            reasons.append("inclusion_transition_root_mismatch")
    except Exception:
        reasons.append("transparency_checkpoint_binding_invalid")

    try:
        leaf_hash = merkle_leaf_hash(canonical_json(manifest))
        result["manifest_leaf_hash"] = leaf_hash.hex()
    except Exception:
        reasons.append("manifest_leaf_hash_invalid")
        leaf_hash = None

    # Only enter the composed verifier after checkpoint binding succeeds. This
    # prevents one inconsistent set of size/root claims from being silently used
    # to parameterize the other gate.
    if not reasons and leaf_hash is not None:
        try:
            gate = verify_transparency_evidence(
                leaf_hash,
                inc["leaf_index"],
                inc["tree_size"],
                inc["root_hash"],
                inc["path"],
                tr["first_size"],
                tr["first_root_hash"],
                tr["consistency_path"],
                tr["witness_observations"],
                tp["witness_keys"],
                tp["minimum_witnesses"],
                tp["log_id"],
                _now_iso(now),
                tp["max_witness_age_seconds"],
                tp["future_tolerance_seconds"],
            )
        except Exception:
            gate = {"valid": False, "reasons": ["transparency_gate_internal_error"], "inclusion": {}, "transition": {}}
        result["inclusion"] = copy.deepcopy(gate.get("inclusion"))
        result["transition"] = copy.deepcopy(gate.get("transition"))
        reasons.extend(gate.get("reasons", []))

    result["valid"] = not reasons
    result["reasons"] = sorted(set(reasons))
    return result


def validate_normalized_manifest(normalized_manifest, backend_contract):
    reasons = []
    if not isinstance(normalized_manifest, Mapping):
        return {"valid": False, "reasons": ["normalized_manifest_invalid"]}
    n = copy.deepcopy(dict(normalized_manifest))
    missing = [k for k in REQUIRED if k not in n]
    if missing:
        reasons.append("normalized_manifest_schema_incomplete:" + ",".join(sorted(missing)))
    prov = n.get("provenance")
    if not isinstance(prov, Mapping):
        reasons.append("provenance_missing")
        return {"valid": False, "reasons": sorted(set(reasons))}
    for key in PROVENANCE_REQUIRED:
        if key not in prov:
            reasons.append("provenance_incomplete:" + key)
    if prov.get("adapter_version") != ADAPTER_VERSION: reasons.append("provenance_adapter_version_mismatch")
    if prov.get("trust_backend") != TRUST_BACKEND: reasons.append("provenance_trust_backend_mismatch")
    if prov.get("inclusion_backend") != INCLUSION_BACKEND: reasons.append("provenance_inclusion_backend_mismatch")
    if prov.get("transition_backend") != TRANSITION_BACKEND: reasons.append("provenance_transition_backend_mismatch")
    if prov.get("transparency_backend") != TRANSPARENCY_BACKEND: reasons.append("provenance_transparency_backend_mismatch")
    if prov.get("collision_backend") != COLLISION_BACKEND: reasons.append("provenance_collision_backend_mismatch")
    if prov.get("inclusion_schema") != INCLUSION_SCHEMA: reasons.append("provenance_inclusion_schema_mismatch")
    if isinstance(backend_contract, Mapping):
        if prov.get("backend_contract_sha256") != _sha_json(dict(backend_contract)):
            reasons.append("provenance_backend_contract_digest_mismatch")
        if prov.get("transparency_policy_sha256") != backend_contract.get("transparency_policy_sha256"):
            reasons.append("provenance_policy_digest_mismatch")
        if prov.get("backend_artifact_sha256") != backend_contract.get("backend_artifact_sha256"):
            reasons.append("provenance_backend_artifact_digest_mismatch")
    else:
        reasons.append("backend_contract_required")
    payload = copy.deepcopy(n)
    payload.pop("provenance", None)
    if prov.get("manifest_sha256") != _sha_json(payload): reasons.append("provenance_manifest_digest_mismatch")
    try:
        expected_leaf = merkle_leaf_hash(canonical_json(payload)).hex()
        if prov.get("manifest_leaf_hash") != expected_leaf:
            reasons.append("provenance_manifest_leaf_hash_mismatch")
    except Exception:
        reasons.append("provenance_manifest_leaf_hash_mismatch")
    if prov.get("source_subject") != payload.get("system_id"): reasons.append("provenance_subject_mismatch")
    return {"valid": not reasons, "reasons": sorted(set(reasons))}


def normalize_trusted_manifest(*, manifest, artifact_bytes, prior_collision_report, attestations,
                               trust_policy, now, transparency_evidence=None, backend_contract=None):
    try:
        if not isinstance(manifest, Mapping): raise TypeError("manifest")
        if not isinstance(prior_collision_report, Mapping): raise TypeError("prior_collision_report")
        if not isinstance(trust_policy, Mapping): raise TypeError("trust_policy")
        if not isinstance(artifact_bytes, (bytes, bytearray, memoryview)): raise TypeError("artifact_bytes")
        if attestations is None or isinstance(attestations, (str, bytes, bytearray, Mapping)): raise TypeError("attestations")
        ats_list = list(attestations)
        if not all(isinstance(x, Mapping) for x in ats_list): raise TypeError("attestation_item")
        if not hasattr(now, "tzinfo"): raise TypeError("now")
        m = copy.deepcopy(dict(manifest))
        art = bytes(artifact_bytes)
        prior = copy.deepcopy(dict(prior_collision_report))
        ats = copy.deepcopy(ats_list)
        pol = copy.deepcopy(dict(trust_policy))
        bc = copy.deepcopy(backend_contract)
    except Exception:
        return {
            "accepted": False, "safe_for_siblings": True, "reasons": ["adapter_input_invalid"],
            "normalized_manifest": None, "trust_evidence": None, "transparency_evidence": None,
            "backend_contract": None,
        }

    reasons = []
    contract = _validate_backend_contract(bc, pol)
    reasons.extend(contract["reasons"])
    runtime_integrity = validate_runtime_dependency_integrity()
    reasons.extend(runtime_integrity["reasons"])
    try:
        trust = verify_attestation_set(ats, m, art, prior, pol, now)
    except Exception:
        trust = {
            "trusted": False, "reasons": ["trust_backend_error"], "valid_signers": [],
            "threshold_required": 0, "threshold_role": "", "boundary_gate": False,
            "non_interference_gate": False,
        }
    trust_schema = validate_trust_result(trust)
    reasons.extend(trust_schema["reasons"])
    reasons.extend(trust.get("reasons", []) if isinstance(trust, Mapping) else ["trust_result_schema_incompatible"])

    missing = [k for k in REQUIRED if k not in m]
    if missing: reasons.append("manifest_schema_incomplete:" + ",".join(sorted(missing)))
    if not isinstance(m.get("interfaces", []), list): reasons.append("manifest_interfaces_invalid")

    tr = _verify_transparency(m, transparency_evidence, pol, now)
    reasons.extend(tr["reasons"])
    accepted = (
        bool(isinstance(trust, Mapping) and trust.get("trusted"))
        and trust_schema["valid"] and tr["valid"] and contract["valid"] and not reasons
    )
    normalized = None
    if accepted:
        normalized = copy.deepcopy(m)
        transition = tr.get("transition") or {}
        witness = transition.get("witness") or {}
        tp = _transparency_policy(pol)
        normalized["provenance"] = {
            "adapter_version": ADAPTER_VERSION,
            "trust_backend": TRUST_BACKEND,
            "inclusion_backend": INCLUSION_BACKEND,
            "transition_backend": TRANSITION_BACKEND,
            "transparency_backend": TRANSPARENCY_BACKEND,
            "collision_backend": COLLISION_BACKEND,
            "inclusion_schema": INCLUSION_SCHEMA,
            "valid_signers": copy.deepcopy(trust.get("valid_signers", [])),
            "threshold_required": trust.get("threshold_required"),
            "source_subject": m.get("system_id"),
            "manifest_sha256": _sha_json(m),
            "manifest_leaf_hash": tr.get("manifest_leaf_hash"),
            "artifact_sha256": hashlib.sha256(art).hexdigest(),
            "transparency_policy_sha256": tr["policy_sha256"],
            "backend_contract_sha256": _sha_json(dict(bc)),
            "backend_artifact_sha256": copy.deepcopy(EXPECTED_DEPENDENCY_SHA256),
            "trusted_checkpoint": copy.deepcopy(tp["trusted_checkpoint"]),
            "current_checkpoint": {
                "tree_size": transparency_evidence["transition"]["second_size"],
                "root_hash": transparency_evidence["transition"]["second_root_hash"],
            },
            "valid_witnesses": copy.deepcopy(witness.get("valid_witnesses", [])),
            "transparency_mode": TRANSPARENCY_BACKEND,
            "attestations_sha256": hash_evidence(ats),
            "prior_collision_report_sha256": hash_evidence(prior),
            "transparency_evidence_sha256": hash_evidence(transparency_evidence),
            "trust_result_sha256": hash_evidence(trust),
            "strict_inclusion_result_sha256": hash_evidence(tr.get("inclusion")),
            "transition_result_sha256": hash_evidence(tr.get("transition")),
        }
        post = validate_normalized_manifest(normalized, bc)
        reasons.extend(post["reasons"])
        if reasons:
            accepted = False
            normalized = None

    return {
        "accepted": accepted,
        "safe_for_siblings": True,
        "reasons": sorted(set(reasons)),
        "normalized_manifest": normalized,
        "trust_evidence": copy.deepcopy(trust),
        "transparency_evidence": copy.deepcopy(tr),
        "backend_contract": copy.deepcopy(contract["expected"]),
        "runtime_dependency_integrity": copy.deepcopy(runtime_integrity),
    }


def analyze_trusted_ecosystem(items, dependency_graph, policy=None):
    normalized = {}
    rejected = {}
    provenance = {}
    contract_digests = {}
    try:
        copied_items = copy.deepcopy(items)
    except Exception:
        return {
            "analysis_performed": False, "safe_for_siblings": True,
            "rejected": {"__input__": ["ecosystem_input_invalid"]}, "collision_report": None,
            "provenance": {}, "evidence_packet": None,
        }
    if not isinstance(copied_items, Mapping):
        return {
            "analysis_performed": False, "safe_for_siblings": True,
            "rejected": {"__input__": ["ecosystem_input_invalid"]}, "collision_report": None,
            "provenance": {}, "evidence_packet": None,
        }
    for name, item in sorted(copied_items.items(), key=lambda kv: str(kv[0])):
        if not isinstance(name, str) or not isinstance(item, Mapping):
            rejected[str(name)] = ["ecosystem_item_invalid"]
            continue
        try:
            r = normalize_trusted_manifest(**item)
        except Exception:
            rejected[name] = ["adapter_boundary_error"]
            continue
        if not r["accepted"]:
            rejected[name] = r["reasons"]
            continue
        n = copy.deepcopy(r["normalized_manifest"])
        check = validate_normalized_manifest(n, item.get("backend_contract"))
        if not check["valid"]:
            rejected[name] = check["reasons"]
            continue
        prov = copy.deepcopy(n.pop("provenance"))
        sid = n.pop("system_id")
        if sid != name:
            rejected[name] = ["manifest_map_identity_mismatch"]
            continue
        normalized[name] = n
        provenance[name] = prov
        contract_digests[name] = _sha_json(dict(item["backend_contract"]))
    if rejected:
        return {
            "analysis_performed": False, "safe_for_siblings": True, "rejected": rejected,
            "collision_report": None, "provenance": provenance, "evidence_packet": None,
        }
    try:
        report = analyze_ecosystem(normalized, copy.deepcopy(dependency_graph), copy.deepcopy(policy))
    except Exception:
        return {
            "analysis_performed": False, "safe_for_siblings": True,
            "rejected": {"__collision__": ["collision_backend_error"]}, "collision_report": None,
            "provenance": provenance, "evidence_packet": None,
        }
    packet = {
        "adapter_version": ADAPTER_VERSION,
        "trust_backend": TRUST_BACKEND,
        "inclusion_backend": INCLUSION_BACKEND,
        "transition_backend": TRANSITION_BACKEND,
        "transparency_backend": TRANSPARENCY_BACKEND,
        "collision_backend": COLLISION_BACKEND,
        "inclusion_schema": INCLUSION_SCHEMA,
        "systems": sorted(normalized),
        "backend_contract_sha256": dict(sorted(contract_digests.items())),
        "backend_artifact_sha256": copy.deepcopy(EXPECTED_DEPENDENCY_SHA256),
        "provenance_sha256": {k: _sha_json(provenance[k]) for k in sorted(provenance)},
        "dependency_graph_sha256": _sha_json(dependency_graph),
        "collision_report_sha256": _sha_json(report),
    }
    packet["evidence_packet_sha256"] = _sha_json(packet)
    return {
        "analysis_performed": True, "safe_for_siblings": True, "rejected": {},
        "collision_report": report, "provenance": provenance, "evidence_packet": packet,
        "collision_backend": COLLISION_BACKEND,
    }
