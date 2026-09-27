"""Merge-specific checks: a DAEDALUS review packet needs BOTH the stale-aware
research lineage binding and the provenance manifest + ancestry binding."""

import pytest

from prometheus_loop.attestation import (
    AttestationVerificationReceipt,
    ExternalExecutionAttestation,
    PluginAttestationPolicy,
)
from prometheus_loop.contracts import (
    CandidateImprovement,
    CandidateStatus,
    LoopKind,
    PromotionStatus,
    ResearchPromotionPacket,
    RunStatus,
    StaleEvidenceReport,
)
from prometheus_loop.fixtures import sample_candidate_profile, sample_observations, sample_plugins
from prometheus_loop.ids import content_id
from prometheus_loop.memory.store import ResearchMemory
from prometheus_loop.orchestration.loop import HostPluginResult, PrometheusLoop, RunInput
from prometheus_loop.plugins import PluginDecisionStatus, PluginExecutionEvidence
from prometheus_loop.policy.promotion import build_research_promotion_packet
from prometheus_loop.provenance import build_research_provenance_manifest
from prometheus_loop.provenance_lineage import ProvenanceLineageReport


def _candidate():
    return CandidateImprovement(
        experiment_id="experiment:1",
        status=CandidateStatus.PROMETHEUS_ENGINEERING_PASS,
        evidence_ids=("adversarial:1", "replay:1"),
        summary="engineering pass only",
    )


def _provenance_kwargs(candidate):
    manifest = build_research_provenance_manifest(
        loop_run_id="loop:1",
        experiment_id=candidate.experiment_id,
        candidate_id=candidate.artifact_id,
        selected_plugin_descriptor_ids=("plugin:1",),
        plugin_evidence_ids=("plugin-evidence:1",),
        plugin_contribution_ids=("plugin-contribution:1",),
        observation_ids=("observation:1",),
    )
    report = ProvenanceLineageReport(
        tip_manifest_id=manifest.artifact_id,
        verified_manifest_ids=(manifest.artifact_id,),
        root_manifest_ids=(manifest.artifact_id,),
        edge_ids=(),
        complete=True,
        failure_reasons=(),
    )
    return dict(
        provenance_manifest=manifest,
        provenance_lineage_report=report,
        loop_run_id="loop:1",
        selected_plugin_descriptor_ids=("plugin:1",),
        observation_ids=("observation:1",),
    )


def _build(candidate, **overrides):
    values = dict(
        run_status=RunStatus.RESEARCH_COMPLETE,
        result=candidate,
        plugin_evidence_ids=("plugin-evidence:1",),
        plugin_contribution_ids=("plugin-contribution:1",),
        lineage_manifest_id="lineage:1",
        stale_report=StaleEvidenceReport(lineage_manifest_id="lineage:1", contract_mismatches=()),
        **_provenance_kwargs(candidate),
    )
    values.update(overrides)
    return build_research_promotion_packet(**values)


def test_valid_provenance_cannot_substitute_for_missing_research_lineage():
    candidate = _candidate()
    with pytest.raises(ValueError, match="research lineage manifest required"):
        _build(candidate, lineage_manifest_id=None, stale_report=None)
    with pytest.raises(ValueError, match="staleness report required"):
        _build(candidate, stale_report=None)


def test_clean_research_lineage_cannot_substitute_for_missing_provenance():
    candidate = _candidate()
    with pytest.raises(ValueError, match="provenance manifest required"):
        _build(candidate, provenance_manifest=None)
    with pytest.raises(ValueError, match="provenance lineage report required"):
        _build(candidate, provenance_lineage_report=None)


def test_stale_research_lineage_suppresses_packet_despite_complete_provenance():
    stale = StaleEvidenceReport(
        lineage_manifest_id="lineage:1",
        contract_mismatches=(("ATHENA", "athena-v1", "athena-v2"),),
    )
    assert _build(_candidate(), stale_report=stale) is None


def test_packet_evidence_binds_both_lineages():
    candidate = _candidate()
    packet = _build(candidate)
    stale = StaleEvidenceReport(lineage_manifest_id="lineage:1", contract_mismatches=())
    assert packet.lineage_manifest_id == "lineage:1"
    assert packet.provenance_manifest_id.startswith("research-provenance:")
    assert packet.provenance_lineage_report_id.startswith("provenance-lineage:")
    assert {
        "lineage:1",
        stale.artifact_id,
        packet.provenance_manifest_id,
        packet.provenance_lineage_report_id,
    } <= set(packet.evidence_ids)


def test_packet_structurally_requires_research_lineage_with_provenance_bindings():
    with pytest.raises(ValueError, match="requires lineage manifest"):
        ResearchPromotionPacket(
            candidate_id="candidate:1",
            target_system="DAEDALUS",
            status=PromotionStatus.READY_FOR_DAEDALUS_REVIEW,
            evidence_ids=("research-provenance:1", "provenance-lineage:1"),
            provenance_manifest_id="research-provenance:1",
            provenance_lineage_report_id="provenance-lineage:1",
            production_authorized=False,
        )


def _strict_attested_run_input():
    objective = "research architecture validation with source-backed analysis"
    observations = sample_observations()
    inventory = sample_plugins()
    profile = sample_candidate_profile()
    policy = PluginAttestationPolicy.REQUIRE_VERIFIED
    loop_run_id = content_id(
        "loop",
        {
            "run_kind": LoopKind.FORGE.value,
            "objective": objective,
            "observations": [item.artifact_id for item in observations],
            "plugins": [item.descriptor_id for item in inventory],
            "candidate_fingerprint": content_id("candidate-profile", profile),
            "source_contract_ids": (),
            "parent_manifest_ids": (),
            "plugin_attestation_policy": policy.value,
        },
    )
    results = []
    for plugin_id, digit in (("deep-research", "a"), ("exa", "b")):
        descriptor = next(item for item in inventory if item.plugin_id == plugin_id)
        evidence = PluginExecutionEvidence(
            loop_run_id=loop_run_id,
            plugin_id=plugin_id,
            plugin_descriptor_id=descriptor.descriptor_id,
            status=PluginDecisionStatus.COMPLETED,
            input_fingerprint=f"input:{plugin_id}",
            output_fingerprint=f"output:{plugin_id}",
        )
        attestation = ExternalExecutionAttestation(
            plugin_evidence_id=evidence.artifact_id,
            subject_sha256=evidence.artifact_id.split(":", 1)[1],
            predicate_type="https://example.invalid/plugin-execution/v1",
            envelope_ref=f"store://attestation/{plugin_id}",
            envelope_sha256=digit * 64,
            verification_material_sha256=digit * 64,
            signer_identity=f"host://{plugin_id}",
            attestation_format="application/vnd.in-toto+json",
        )
        receipt = AttestationVerificationReceipt(
            attestation_id=attestation.artifact_id,
            verifier_id="verifier://fixture/v1",
            trusted_root_id="trust-root://fixture/v1",
            verification_policy_id="policy://fixture/v1",
            checks=(("signature", True), ("subject_digest", True), ("signer_identity", True), ("trusted_root", True)),
            external_verification_ref=f"store://verification/{plugin_id}",
        )
        results.append(
            HostPluginResult(
                plugin_id=plugin_id,
                success=True,
                input_fingerprint=f"input:{plugin_id}",
                output_fingerprint=f"output:{plugin_id}",
                external_attestation=attestation,
                attestation_verification=receipt,
            )
        )
    return RunInput(
        run_kind=LoopKind.FORGE,
        objective=objective,
        observations=observations,
        plugin_inventory=inventory,
        plugin_results=tuple(results),
        candidate_profile=profile,
        baseline_metrics=(("score", 0.50),),
        candidate_metrics=(("score", 0.60),),
        plugin_attestation_policy=policy,
    )


def test_live_strict_attested_loop_packet_binds_route_lineage_and_provenance(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    run = PrometheusLoop(memory).run(_strict_attested_run_input())

    assert run.status is RunStatus.RESEARCH_COMPLETE
    assert run.route.artifact_id
    assert run.stale_evidence_report.is_stale is False
    packet = run.promotion_packet
    assert packet is not None
    assert packet.production_authorized is False
    assert packet.lineage_manifest_id == run.lineage_manifest_id
    assert packet.provenance_manifest_id == run.provenance_manifest_id
    assert packet.provenance_lineage_report_id == run.provenance_lineage_report_id
    assert {
        run.lineage_manifest_id,
        run.stale_evidence_report.artifact_id,
        run.provenance_manifest_id,
        run.provenance_lineage_report_id,
        *run.external_attestation_ids,
        *run.attestation_verification_ids,
    } <= set(packet.evidence_ids)

    lineage = memory.find_by_id(run.lineage_manifest_id)["payload"]
    assert set(run.external_attestation_ids) <= set(lineage["artifact_ids"])
    assert set(run.attestation_verification_ids) <= set(lineage["artifact_ids"])
    assert run.route.artifact_id in lineage["artifact_ids"]
