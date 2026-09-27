import pytest

from prometheus_loop.attestation import PluginAttestationPolicy
from prometheus_loop.contracts import (
    CandidateImprovement,
    CandidateStatus,
    PromotionStatus,
    RejectedHypothesis,
    ResearchPromotionPacket,
    RunStatus,
    StaleEvidenceReport,
)
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


def _manifest(candidate=None, **overrides):
    candidate = candidate or _candidate()
    values = dict(
        loop_run_id="loop:1",
        experiment_id=candidate.experiment_id,
        candidate_id=candidate.artifact_id,
        selected_plugin_descriptor_ids=("plugin:1",),
        plugin_evidence_ids=("plugin-evidence:1",),
        plugin_contribution_ids=("plugin-contribution:1",),
        observation_ids=("observation:1",),
        source_contract_ids=("nexus-contract:1",),
        parent_manifest_ids=(),
        external_attestation_ids=(),
        attestation_verification_ids=(),
        plugin_attestation_policy=PluginAttestationPolicy.OPTIONAL,
    )
    values.update(overrides)
    return build_research_provenance_manifest(**values)


def _lineage(manifest, *, complete=True, tip_manifest_id=None):
    tip = tip_manifest_id or manifest.artifact_id
    verified = {manifest.artifact_id, *manifest.parent_manifest_ids} if complete else {manifest.artifact_id}
    roots = set(manifest.parent_manifest_ids) if manifest.parent_manifest_ids else {manifest.artifact_id}
    return ProvenanceLineageReport(
        tip_manifest_id=tip,
        verified_manifest_ids=tuple(verified),
        root_manifest_ids=tuple(roots if complete else ()),
        edge_ids=tuple(f"{parent} -> {manifest.artifact_id}" for parent in manifest.parent_manifest_ids),
        complete=complete,
        failure_reasons=() if complete else ("missing parent manifest",),
    )


def _build_packet(candidate=None, manifest=None, lineage_report=None, **overrides):
    candidate = candidate or _candidate()
    manifest = manifest or _manifest(candidate)
    lineage_report = lineage_report or _lineage(manifest)
    values = dict(
        run_status=RunStatus.RESEARCH_COMPLETE,
        result=candidate,
        provenance_manifest=manifest,
        provenance_lineage_report=lineage_report,
        loop_run_id="loop:1",
        selected_plugin_descriptor_ids=("plugin:1",),
        plugin_evidence_ids=("plugin-evidence:1",),
        plugin_contribution_ids=("plugin-contribution:1",),
        observation_ids=("observation:1",),
        source_contract_ids=("nexus-contract:1",),
        parent_manifest_ids=(),
        external_attestation_ids=(),
        attestation_verification_ids=(),
        plugin_attestation_policy=PluginAttestationPolicy.OPTIONAL,
        # unified merge: the stale-aware lineage binding is also mandatory
        lineage_manifest_id="lineage:1",
        stale_report=StaleEvidenceReport(lineage_manifest_id="lineage:1", contract_mismatches=()),
    )
    values.update(overrides)
    return build_research_promotion_packet(**values)


def test_complete_engineering_pass_emits_daedalus_review_packet():
    candidate = _candidate()
    manifest = _manifest(candidate)
    packet = build_research_promotion_packet(
        run_status=RunStatus.RESEARCH_COMPLETE,
        result=candidate,
        plugin_evidence_ids=("plugin-evidence:1",),
        plugin_contribution_ids=("plugin-contribution:1",),
        lineage_manifest_id="lineage:1",
        stale_report=StaleEvidenceReport(lineage_manifest_id="lineage:1", contract_mismatches=()),
        # unified merge: the provenance manifest + ancestry binding is also mandatory
        provenance_manifest=manifest,
        provenance_lineage_report=_lineage(manifest),
        loop_run_id="loop:1",
        selected_plugin_descriptor_ids=("plugin:1",),
        observation_ids=("observation:1",),
        source_contract_ids=("nexus-contract:1",),
    )
    assert packet is not None
    assert packet.status is PromotionStatus.READY_FOR_DAEDALUS_REVIEW
    assert packet.target_system == "DAEDALUS"
    assert packet.candidate_id == candidate.artifact_id
    assert packet.production_authorized is False
    assert packet.lineage_manifest_id == "lineage:1"
    assert set(packet.evidence_ids) >= {
        candidate.artifact_id,
        "adversarial:1",
        "replay:1",
        "plugin-evidence:1",
        "plugin-contribution:1",
    }


def test_complete_engineering_pass_emits_lineage_and_provenance_bound_daedalus_review_packet():
    candidate = _candidate()
    manifest = _manifest(candidate)
    lineage = _lineage(manifest)
    packet = _build_packet(candidate, manifest, lineage)

    assert packet is not None
    assert packet.status is PromotionStatus.READY_FOR_DAEDALUS_REVIEW
    assert packet.target_system == "DAEDALUS"
    assert packet.candidate_id == candidate.artifact_id
    assert packet.provenance_manifest_id == manifest.artifact_id
    assert packet.provenance_lineage_report_id == lineage.artifact_id
    assert packet.production_authorized is False
    assert set(packet.evidence_ids) >= {
        candidate.artifact_id,
        "adversarial:1",
        "replay:1",
        "plugin-evidence:1",
        "plugin-contribution:1",
        manifest.artifact_id,
        lineage.artifact_id,
    }


@pytest.mark.parametrize(
    "manifest_overrides,error",
    [
        ({"loop_run_id": "loop:stale"}, "loop run"),
        ({"experiment_id": "experiment:stale"}, "experiment"),
        ({"candidate_id": "candidate:stale"}, "candidate"),
        ({"selected_plugin_descriptor_ids": ("plugin:stale",)}, "descriptor"),
        ({"plugin_evidence_ids": ("plugin-evidence:stale",)}, "plugin evidence"),
        ({"plugin_contribution_ids": ("plugin-contribution:stale",)}, "contribution"),
        ({"observation_ids": ("observation:stale",)}, "observation"),
        ({"source_contract_ids": ("nexus-contract:stale",)}, "source contract"),
        ({"parent_manifest_ids": ("research-provenance:stale",)}, "parent manifest"),
        ({"external_attestation_ids": ("external-attestation:stale",), "attestation_verification_ids": ("attestation-verification:stale",)}, "external attestation"),
        ({"plugin_attestation_policy": PluginAttestationPolicy.REQUIRE_VERIFIED, "external_attestation_ids": ("external-attestation:1",), "attestation_verification_ids": ("attestation-verification:1",)}, "external attestation"),
    ],
)
def test_promotion_builder_rejects_stale_or_tampered_manifest(manifest_overrides, error):
    candidate = _candidate()
    manifest = _manifest(candidate, **manifest_overrides)
    with pytest.raises(ValueError, match=error):
        _build_packet(candidate, manifest, _lineage(manifest))



def test_promotion_builder_rejects_attestation_policy_mismatch_after_evidence_matches():
    candidate = _candidate()
    manifest = _manifest(
        candidate,
        plugin_attestation_policy=PluginAttestationPolicy.REQUIRE_VERIFIED,
        external_attestation_ids=("external-attestation:1",),
        attestation_verification_ids=("attestation-verification:1",),
    )
    with pytest.raises(ValueError, match="attestation policy"):
        _build_packet(
            candidate,
            manifest,
            _lineage(manifest),
            external_attestation_ids=("external-attestation:1",),
            attestation_verification_ids=("attestation-verification:1",),
            plugin_attestation_policy=PluginAttestationPolicy.OPTIONAL,
        )

def test_promotion_builder_requires_manifest_and_lineage_for_eligible_candidate():
    candidate = _candidate()
    manifest = _manifest(candidate)
    with pytest.raises(ValueError, match="provenance manifest required"):
        _build_packet(candidate, provenance_manifest=None, manifest=None)
    with pytest.raises(ValueError, match="lineage report required"):
        _build_packet(candidate, manifest, provenance_lineage_report=None, lineage_report=None)


def test_promotion_builder_rejects_incomplete_or_wrong_tip_lineage():
    candidate = _candidate()
    manifest = _manifest(candidate)
    with pytest.raises(ValueError, match="lineage.*incomplete"):
        _build_packet(candidate, manifest, _lineage(manifest, complete=False))
    with pytest.raises(ValueError, match="lineage.*tip"):
        _build_packet(
            candidate,
            manifest,
            _lineage(manifest, tip_manifest_id="research-provenance:" + "f" * 64),
        )


def test_degraded_or_rejected_run_emits_no_packet_without_manifest_or_lineage():
    candidate = _candidate()
    assert build_research_promotion_packet(
        run_status=RunStatus.DEGRADED_RESEARCH,
        result=candidate,
        provenance_manifest=None,
        provenance_lineage_report=None,
        loop_run_id="loop:1",
        selected_plugin_descriptor_ids=(),
        plugin_evidence_ids=(),
        plugin_contribution_ids=(),
        observation_ids=("observation:1",),
        source_contract_ids=(),
        parent_manifest_ids=(),
        external_attestation_ids=(),
        attestation_verification_ids=(),
        plugin_attestation_policy=PluginAttestationPolicy.OPTIONAL,
    ) is None
    rejected = RejectedHypothesis(
        experiment_id="experiment:2",
        reason="failed guardrail",
        evidence_ids=("replay:2",),
    )
    assert build_research_promotion_packet(
        run_status=RunStatus.RESEARCH_COMPLETE,
        result=rejected,
        provenance_manifest=None,
        provenance_lineage_report=None,
        loop_run_id="loop:1",
        selected_plugin_descriptor_ids=(),
        plugin_evidence_ids=(),
        plugin_contribution_ids=(),
        observation_ids=("observation:1",),
        source_contract_ids=(),
        parent_manifest_ids=(),
        external_attestation_ids=(),
        attestation_verification_ids=(),
        plugin_attestation_policy=PluginAttestationPolicy.OPTIONAL,
    ) is None


def test_promotion_packet_requires_matching_manifest_and_lineage_evidence():
    with pytest.raises(ValueError, match="provenance manifest"):
        ResearchPromotionPacket(
            candidate_id="candidate:1",
            target_system="DAEDALUS",
            status=PromotionStatus.READY_FOR_DAEDALUS_REVIEW,
            evidence_ids=("provenance-lineage:1",),
            provenance_manifest_id="research-provenance:1",
            provenance_lineage_report_id="provenance-lineage:1",
            production_authorized=False,
        )
    with pytest.raises(ValueError, match="lineage report"):
        ResearchPromotionPacket(
            candidate_id="candidate:1",
            target_system="DAEDALUS",
            status=PromotionStatus.READY_FOR_DAEDALUS_REVIEW,
            evidence_ids=("research-provenance:1",),
            provenance_manifest_id="research-provenance:1",
            provenance_lineage_report_id="provenance-lineage:1",
            production_authorized=False,
        )


def test_degraded_or_rejected_run_emits_no_packet():
    candidate = _candidate()
    assert build_research_promotion_packet(
        run_status=RunStatus.DEGRADED_RESEARCH,
        result=candidate,
        plugin_evidence_ids=(),
        plugin_contribution_ids=(),
        lineage_manifest_id="lineage:1",
        stale_report=StaleEvidenceReport(lineage_manifest_id="lineage:1", contract_mismatches=()),
    ) is None
    rejected = RejectedHypothesis(
        experiment_id="experiment:2",
        reason="failed guardrail",
        evidence_ids=("replay:2",),
    )
    assert build_research_promotion_packet(
        run_status=RunStatus.RESEARCH_COMPLETE,
        result=rejected,
        plugin_evidence_ids=(),
        plugin_contribution_ids=(),
        lineage_manifest_id="lineage:1",
        stale_report=StaleEvidenceReport(lineage_manifest_id="lineage:1", contract_mismatches=()),
    ) is None


def test_promotion_packet_cannot_authorize_production():
    assert tuple(PromotionStatus) == (PromotionStatus.READY_FOR_DAEDALUS_REVIEW,)
    with pytest.raises(ValueError, match="production authorization"):
        ResearchPromotionPacket(
            candidate_id="candidate:1",
            target_system="DAEDALUS",
            status=PromotionStatus.READY_FOR_DAEDALUS_REVIEW,
            evidence_ids=("evidence:1", "research-provenance:1", "provenance-lineage:1"),
            lineage_manifest_id="lineage:1",
            provenance_manifest_id="research-provenance:1",
            provenance_lineage_report_id="provenance-lineage:1",
            production_authorized=True,
        )


def test_promotion_rejects_staleness_report_for_different_lineage():
    with pytest.raises(ValueError, match="staleness report does not match lineage manifest"):
        build_research_promotion_packet(
            run_status=RunStatus.RESEARCH_COMPLETE,
            result=_candidate(),
            plugin_evidence_ids=(),
            plugin_contribution_ids=(),
            lineage_manifest_id="lineage:expected",
            stale_report=StaleEvidenceReport(
                lineage_manifest_id="lineage:other",
                contract_mismatches=(),
            ),
        )
