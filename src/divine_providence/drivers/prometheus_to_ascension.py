"""PROMETHEUS runtime provenance -> ASCENSION structural conformance.

This driver executes PROMETHEUS's actual strict-attested research path against
its deterministic internal fixture, writes the resulting runtime artifacts to
append-only ResearchMemory, emits an exact byte-bound PROMETHEUS handoff, and
feeds that untouched export into ASCENSION's Sibling Manifest Conformance Kit.

The external-attestation records in this deterministic fixture are contract
fixtures, not cryptographic authentication. The driver must therefore end at
STRUCTURALLY_CONFORMANT with Transfer blocked and authenticated=false.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

import sibling_manifest_conformance_v0_1 as kit

from prometheus_loop.attestation import (
    AttestationVerificationReceipt,
    ExternalExecutionAttestation,
    PluginAttestationPolicy,
)
from prometheus_loop.contracts import LoopKind, RunStatus
from prometheus_loop.fixtures import (
    sample_candidate_profile,
    sample_observations,
    sample_plugins,
)
from prometheus_loop.handoff import build_ascension_handoff_export
from prometheus_loop.ids import content_id
from prometheus_loop.memory.store import ResearchMemory
from prometheus_loop.orchestration.loop import (
    HostPluginResult,
    PrometheusLoop,
    RunInput,
)
from prometheus_loop.plugins import (
    PluginDecisionStatus,
    PluginExecutionEvidence,
)
from prometheus_loop.policy.plugins import PluginSelectionPolicy

from ._common import emit


OBJECTIVE = "research architecture validation with source-backed analysis"
POLICY = PluginAttestationPolicy.REQUIRE_VERIFIED


def _strict_runtime_input() -> RunInput:
    observations = sample_observations()
    inventory = sample_plugins()
    candidate_profile = sample_candidate_profile()
    decisions = PluginSelectionPolicy().select(
        LoopKind.FORGE,
        OBJECTIVE,
        inventory,
    )
    selected = [
        item
        for item in decisions
        if item.status is PluginDecisionStatus.SELECTED
    ]
    if not selected:
        raise ValueError("PROMETHEUS fixture selected no research plugins")

    loop_run_id = content_id(
        "loop",
        {
            "run_kind": LoopKind.FORGE.value,
            "objective": OBJECTIVE,
            "observations": [item.artifact_id for item in observations],
            "plugins": [item.descriptor_id for item in inventory],
            "candidate_fingerprint": content_id(
                "candidate-profile", candidate_profile
            ),
            "source_contract_ids": (),
            "parent_manifest_ids": (),
            "plugin_attestation_policy": POLICY.value,
        },
    )

    results: list[HostPluginResult] = []
    descriptor_by_id = {item.plugin_id: item for item in inventory}
    for decision in selected:
        descriptor = descriptor_by_id[decision.plugin_id]
        evidence = PluginExecutionEvidence(
            loop_run_id=loop_run_id,
            plugin_id=decision.plugin_id,
            plugin_descriptor_id=descriptor.descriptor_id,
            status=PluginDecisionStatus.COMPLETED,
            input_fingerprint=f"fixture-input:{decision.plugin_id}",
            output_fingerprint=f"fixture-output:{decision.plugin_id}",
        )
        subject_sha256 = evidence.artifact_id.split(":", 1)[1]
        envelope_sha256 = hashlib.sha256(
            f"fixture-envelope:{decision.plugin_id}".encode("utf-8")
        ).hexdigest()
        material_sha256 = hashlib.sha256(
            f"fixture-verification-material:{decision.plugin_id}".encode("utf-8")
        ).hexdigest()
        attestation = ExternalExecutionAttestation(
            plugin_evidence_id=evidence.artifact_id,
            subject_sha256=subject_sha256,
            predicate_type="https://example.invalid/prometheus/plugin-execution/v1",
            envelope_ref=f"fixture://attestation/{decision.plugin_id}",
            envelope_sha256=envelope_sha256,
            verification_material_sha256=material_sha256,
            signer_identity=f"fixture://host/{decision.plugin_id}",
            attestation_format="application/vnd.in-toto+json",
        )
        receipt = AttestationVerificationReceipt(
            attestation_id=attestation.artifact_id,
            verifier_id="fixture://external-verifier/v1",
            trusted_root_id="fixture://trust-root/v1",
            verification_policy_id="fixture://require-verified/v1",
            checks=(
                ("signature", True),
                ("subject_digest", True),
                ("signer_identity", True),
                ("trusted_root", True),
            ),
            external_verification_ref=(
                f"fixture://verification/{decision.plugin_id}"
            ),
        )
        results.append(
            HostPluginResult(
                plugin_id=decision.plugin_id,
                success=True,
                input_fingerprint=f"fixture-input:{decision.plugin_id}",
                output_fingerprint=f"fixture-output:{decision.plugin_id}",
                external_attestation=attestation,
                attestation_verification=receipt,
            )
        )

    return RunInput(
        run_kind=LoopKind.FORGE,
        objective=OBJECTIVE,
        observations=observations,
        plugin_inventory=inventory,
        plugin_results=tuple(results),
        candidate_profile=candidate_profile,
        baseline_metrics=(("score", 0.50),),
        candidate_metrics=(("score", 0.60),),
        plugin_attestation_policy=POLICY,
    )


with TemporaryDirectory() as directory:
    memory = ResearchMemory(Path(directory) / "prometheus-runtime.jsonl")
    run = PrometheusLoop(memory).run(_strict_runtime_input())
    if run.status is not RunStatus.RESEARCH_COMPLETE:
        raise ValueError(
            f"PROMETHEUS strict runtime fixture degraded: {run.status.value}"
        )
    if run.provenance_manifest_id is None:
        raise ValueError("PROMETHEUS strict runtime emitted no provenance manifest")
    if not run.plugin_evidence_ids:
        raise ValueError("PROMETHEUS strict runtime emitted no plugin evidence")

    plugin_evidence_id = run.plugin_evidence_ids[0]
    export = build_ascension_handoff_export(
        memory,
        provenance_manifest_id=run.provenance_manifest_id,
        plugin_evidence_id=plugin_evidence_id,
    )
    result = kit.validate_export(export)

expected_status = "STRUCTURALLY_CONFORMANT"
ok = (
    result.get("conformant") is True
    and result.get("status") == expected_status
    and result.get("ready_for_adapter_v0_4") is False
    and result.get("authenticated") is False
)
emit(
    {
        "connection": "prometheus->ascension",
        "ok": ok,
        "runtime_export_generated": True,
        "runtime_fixture_kind": "deterministic_internal_contract_fixture",
        "provenance_manifest_id": run.provenance_manifest_id,
        "plugin_evidence_id": plugin_evidence_id,
        "artifact_sha256": export["artifact"]["sha256"],
        "ascension_status": result.get("status"),
        "conformant": result.get("conformant"),
        "ready_for_adapter_v0_4": result.get("ready_for_adapter_v0_4"),
        "authenticated": False,
        "transfer": (
            "BLOCKED: exact PROMETHEUS runtime bytes now cross the structural "
            "handoff, but ASCENSION-authorized trust policy, cryptographic "
            "verification material, collision verdict, strict inclusion proof, "
            "and independent witness/transition evidence are still required"
        ),
        "warnings": result.get("warnings", []),
        "reasons": result.get("reasons", []),
        "execution_authorized": False,
        "production_decision_authorized": False,
    }
)
