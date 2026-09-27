from __future__ import annotations

from ..attestation import PluginAttestationPolicy
from ..contracts import (
    CandidateImprovement,
    CandidateStatus,
    PromotionStatus,
    RejectedHypothesis,
    ResearchPromotionPacket,
    ResearchProvenanceManifest,
    RunStatus,
    StaleEvidenceReport,
)
from ..provenance_lineage import ProvenanceLineageReport


def _canonical_ids(label: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label} identifiers")
    return tuple(sorted(values))


def _require_manifest_match(
    manifest: ResearchProvenanceManifest,
    *,
    result: CandidateImprovement,
    loop_run_id: str | None,
    selected_plugin_descriptor_ids: tuple[str, ...],
    plugin_evidence_ids: tuple[str, ...],
    plugin_contribution_ids: tuple[str, ...],
    observation_ids: tuple[str, ...],
    source_contract_ids: tuple[str, ...],
    parent_manifest_ids: tuple[str, ...],
    external_attestation_ids: tuple[str, ...],
    attestation_verification_ids: tuple[str, ...],
    plugin_attestation_policy: PluginAttestationPolicy,
) -> None:
    if manifest.loop_run_id != loop_run_id:
        raise ValueError("provenance manifest loop run mismatch")
    if manifest.experiment_id != result.experiment_id:
        raise ValueError("provenance manifest experiment mismatch")
    if manifest.candidate_id != result.artifact_id:
        raise ValueError("provenance manifest candidate mismatch")
    expected = (
        ("descriptor", manifest.selected_plugin_descriptor_ids, selected_plugin_descriptor_ids),
        ("plugin evidence", manifest.plugin_evidence_ids, plugin_evidence_ids),
        ("contribution", manifest.plugin_contribution_ids, plugin_contribution_ids),
        ("observation", manifest.observation_ids, observation_ids),
        ("source contract", manifest.source_contract_ids, source_contract_ids),
        ("parent manifest", manifest.parent_manifest_ids, parent_manifest_ids),
        ("external attestation", manifest.external_attestation_ids, external_attestation_ids),
        ("attestation verification", manifest.attestation_verification_ids, attestation_verification_ids),
    )
    for label, observed, current in expected:
        if observed != _canonical_ids(label, current):
            raise ValueError(f"provenance manifest {label} mismatch")
    if manifest.plugin_attestation_policy is not PluginAttestationPolicy(plugin_attestation_policy):
        raise ValueError("provenance manifest attestation policy mismatch")


def build_research_promotion_packet(
    *,
    run_status: RunStatus,
    result: CandidateImprovement | RejectedHypothesis,
    plugin_evidence_ids: tuple[str, ...],
    plugin_contribution_ids: tuple[str, ...],
    lineage_manifest_id: str | None = None,
    stale_report: StaleEvidenceReport | None = None,
    provenance_manifest: ResearchProvenanceManifest | None = None,
    provenance_lineage_report: ProvenanceLineageReport | None = None,
    loop_run_id: str | None = None,
    selected_plugin_descriptor_ids: tuple[str, ...] = (),
    observation_ids: tuple[str, ...] = (),
    source_contract_ids: tuple[str, ...] = (),
    parent_manifest_ids: tuple[str, ...] = (),
    external_attestation_ids: tuple[str, ...] = (),
    attestation_verification_ids: tuple[str, ...] = (),
    plugin_attestation_policy: PluginAttestationPolicy = PluginAttestationPolicy.OPTIONAL,
) -> ResearchPromotionPacket | None:
    """Build a DAEDALUS review packet only when BOTH research bindings hold.

    * stale-aware research lineage: a concrete ``ResearchLineageManifest`` ID and
      a clean ``StaleEvidenceReport`` bound to that exact manifest; and
    * provenance attestation lineage: a ``ResearchProvenanceManifest`` matching
      the live run inputs plus a complete ``ProvenanceLineageReport`` whose tip
      is that manifest.

    Binding inputs default to ``None``/empty only so non-eligible runs can
    return ``None`` without fabricating evidence; an eligible candidate that is
    missing either binding fails closed.
    """
    if stale_report is not None and stale_report.lineage_manifest_id != lineage_manifest_id:
        raise ValueError("staleness report does not match lineage manifest")
    if run_status is not RunStatus.RESEARCH_COMPLETE:
        return None
    if stale_report is not None and stale_report.is_stale:
        return None
    if not isinstance(result, CandidateImprovement):
        return None
    if result.status is not CandidateStatus.PROMETHEUS_ENGINEERING_PASS:
        return None
    if not lineage_manifest_id:
        raise ValueError("research lineage manifest required for DAEDALUS review")
    if stale_report is None:
        raise ValueError("staleness report required for DAEDALUS review")
    if provenance_manifest is None:
        raise ValueError("provenance manifest required for DAEDALUS review")
    if provenance_lineage_report is None:
        raise ValueError("provenance lineage report required for DAEDALUS review")

    _require_manifest_match(
        provenance_manifest,
        result=result,
        loop_run_id=loop_run_id,
        selected_plugin_descriptor_ids=selected_plugin_descriptor_ids,
        plugin_evidence_ids=plugin_evidence_ids,
        plugin_contribution_ids=plugin_contribution_ids,
        observation_ids=observation_ids,
        source_contract_ids=source_contract_ids,
        parent_manifest_ids=parent_manifest_ids,
        external_attestation_ids=external_attestation_ids,
        attestation_verification_ids=attestation_verification_ids,
        plugin_attestation_policy=plugin_attestation_policy,
    )
    if not provenance_lineage_report.complete:
        raise ValueError("provenance lineage is incomplete")
    if provenance_lineage_report.tip_manifest_id != provenance_manifest.artifact_id:
        raise ValueError("provenance lineage tip mismatch")
    if provenance_manifest.artifact_id not in provenance_lineage_report.verified_manifest_ids:
        raise ValueError("provenance lineage does not verify current manifest")
    missing_direct = set(provenance_manifest.parent_manifest_ids) - set(provenance_lineage_report.verified_manifest_ids)
    if missing_direct:
        raise ValueError("provenance lineage does not verify direct parent manifests")

    evidence_ids = tuple(sorted({
        result.artifact_id,
        *result.evidence_ids,
        *plugin_evidence_ids,
        *plugin_contribution_ids,
        *external_attestation_ids,
        *attestation_verification_ids,
        lineage_manifest_id,
        stale_report.artifact_id,
        provenance_manifest.artifact_id,
        provenance_lineage_report.artifact_id,
    }))
    return ResearchPromotionPacket(
        candidate_id=result.artifact_id,
        target_system="DAEDALUS",
        status=PromotionStatus.READY_FOR_DAEDALUS_REVIEW,
        evidence_ids=evidence_ids,
        lineage_manifest_id=lineage_manifest_id,
        provenance_manifest_id=provenance_manifest.artifact_id,
        provenance_lineage_report_id=provenance_lineage_report.artifact_id,
        production_authorized=False,
    )
