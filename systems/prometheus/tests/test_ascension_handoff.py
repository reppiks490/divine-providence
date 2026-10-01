from __future__ import annotations

import base64
import hashlib
import importlib.util
from pathlib import Path

import pytest

from prometheus_loop.attestation import (
    AttestationVerificationReceipt,
    ExternalExecutionAttestation,
    PluginAttestationPolicy,
)
from prometheus_loop.handoff import build_ascension_handoff_export
from prometheus_loop.ids import canonical_json
from prometheus_loop.memory.store import ResearchMemory
from prometheus_loop.plugins import PluginDecisionStatus, PluginExecutionEvidence
from prometheus_loop.provenance import build_research_provenance_manifest


def _load_ascension_conformance():
    path = (
        Path(__file__).resolve().parents[2]
        / "ascension"
        / "sibling_manifest_conformance_v0_1.py"
    )
    spec = importlib.util.spec_from_file_location(
        "ascension_sibling_manifest_conformance_v0_1", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_memory(
    tmp_path,
    *,
    policy: PluginAttestationPolicy = PluginAttestationPolicy.REQUIRE_VERIFIED,
    verified: bool = True,
):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    evidence = PluginExecutionEvidence(
        loop_run_id="loop:1",
        plugin_id="deep-research",
        plugin_descriptor_id="plugin:1",
        status=PluginDecisionStatus.COMPLETED,
        input_fingerprint="input:1",
        output_fingerprint="output:1",
    )
    subject_sha256 = evidence.artifact_id.split(":", 1)[1]
    attestation = ExternalExecutionAttestation(
        plugin_evidence_id=evidence.artifact_id,
        subject_sha256=subject_sha256,
        predicate_type="https://example.invalid/prometheus/plugin-execution/v1",
        envelope_ref="store://attestation/deep-research",
        envelope_sha256="b" * 64,
        verification_material_sha256="c" * 64,
        signer_identity="host://deep-research",
        attestation_format="application/vnd.in-toto+json",
    )
    receipt = AttestationVerificationReceipt(
        attestation_id=attestation.artifact_id,
        verifier_id="verifier://fixture/v1",
        trusted_root_id="trust-root://fixture/v1",
        verification_policy_id="policy://fixture/v1",
        checks=(
            ("signature", verified),
            ("subject_digest", True),
            ("signer_identity", True),
            ("trusted_root", True),
        ),
        external_verification_ref="store://verification/deep-research",
    )
    manifest = build_research_provenance_manifest(
        loop_run_id="loop:1",
        experiment_id="experiment:1",
        candidate_id="candidate:1",
        selected_plugin_descriptor_ids=("plugin:1",),
        plugin_evidence_ids=(evidence.artifact_id,),
        plugin_contribution_ids=("plugin-contribution:1",),
        observation_ids=("observation:1",),
        source_contract_ids=("nexus-contract:" + "d" * 64,),
        external_attestation_ids=(attestation.artifact_id,),
        attestation_verification_ids=(receipt.artifact_id,),
        plugin_attestation_policy=policy,
    )
    for artifact in (evidence, attestation, receipt, manifest):
        memory.append(artifact)
    return memory, evidence, manifest


def test_runtime_export_is_exact_and_structurally_conformant(tmp_path):
    memory, evidence, manifest = _runtime_memory(tmp_path)

    export = build_ascension_handoff_export(
        memory,
        provenance_manifest_id=manifest.artifact_id,
        plugin_evidence_id=evidence.artifact_id,
    )

    raw = base64.b64decode(export["artifact"]["content_b64"], validate=True)
    expected = canonical_json(memory.find_by_id(manifest.artifact_id)["payload"]).encode(
        "utf-8"
    )
    assert raw == expected
    assert export["artifact"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert export["authority"]["attestation"]["plugin_evidence_id"] == evidence.artifact_id
    assert export["extensions"]["prometheus"]["authenticated"] is False
    assert export["extensions"]["prometheus"]["transfer_verified"] is False
    assert export["extensions"]["prometheus"]["production_authorized"] is False
    assert "adapter_v0_4_evidence" not in export

    conformance = _load_ascension_conformance()
    result = conformance.validate_export(export)
    assert result["conformant"] is True
    assert result["status"] == "STRUCTURALLY_CONFORMANT"
    assert result["ready_for_adapter_v0_4"] is False
    assert result["authenticated"] is False


def test_handoff_rejects_non_strict_provenance(tmp_path):
    memory, evidence, manifest = _runtime_memory(
        tmp_path, policy=PluginAttestationPolicy.OPTIONAL
    )
    with pytest.raises(ValueError, match="REQUIRE_VERIFIED"):
        build_ascension_handoff_export(
            memory,
            provenance_manifest_id=manifest.artifact_id,
            plugin_evidence_id=evidence.artifact_id,
        )


def test_handoff_rejects_failed_external_verification(tmp_path):
    memory, evidence, manifest = _runtime_memory(tmp_path, verified=False)
    with pytest.raises(ValueError, match="not verified"):
        build_ascension_handoff_export(
            memory,
            provenance_manifest_id=manifest.artifact_id,
            plugin_evidence_id=evidence.artifact_id,
        )


def test_handoff_rejects_evidence_not_bound_to_manifest(tmp_path):
    memory, _, manifest = _runtime_memory(tmp_path)
    other = PluginExecutionEvidence(
        loop_run_id="loop:1",
        plugin_id="other",
        plugin_descriptor_id="plugin:other",
        status=PluginDecisionStatus.COMPLETED,
        input_fingerprint="input:other",
        output_fingerprint="output:other",
    )
    memory.append(other)
    with pytest.raises(ValueError, match="not bound"):
        build_ascension_handoff_export(
            memory,
            provenance_manifest_id=manifest.artifact_id,
            plugin_evidence_id=other.artifact_id,
        )
