from __future__ import annotations

from .attestation import PluginAttestationPolicy
from .contracts import ResearchProvenanceManifest


def build_research_provenance_manifest(
    *,
    loop_run_id: str,
    experiment_id: str,
    candidate_id: str,
    selected_plugin_descriptor_ids: tuple[str, ...],
    plugin_evidence_ids: tuple[str, ...],
    plugin_contribution_ids: tuple[str, ...],
    observation_ids: tuple[str, ...],
    source_contract_ids: tuple[str, ...] = (),
    parent_manifest_ids: tuple[str, ...] = (),
    external_attestation_ids: tuple[str, ...] = (),
    attestation_verification_ids: tuple[str, ...] = (),
    plugin_attestation_policy: PluginAttestationPolicy = PluginAttestationPolicy.OPTIONAL,
) -> ResearchProvenanceManifest:
    return ResearchProvenanceManifest(
        loop_run_id=loop_run_id,
        experiment_id=experiment_id,
        candidate_id=candidate_id,
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
