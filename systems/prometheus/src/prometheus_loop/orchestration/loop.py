from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..adapters.nexus import validate_nexus_bundle
from ..attestation import (
    AttestationVerificationReceipt,
    ExternalExecutionAttestation,
    PluginAttestationPolicy,
    validate_external_attestation_binding,
)
from ..adapters.siblings import normalize_nexus_bundle

from ..contracts import (
    CandidateImprovement,
    CandidateStatus,
    DeferredExperiment,
    DisagreementCase,
    DisagreementDiagnosis,
    ExperimentRouteAction,
    ExperimentRouteDecision,
    ExperimentSpec,
    LoopKind,
    RejectedHypothesis,
    ResearchHypothesis,
    ResearchPromotionPacket,
    RunStatus,
    StaleEvidenceReport,
)
from ..forge.adversarial import run_adversarial
from ..forge.hypothesis import hypothesis_from_case
from ..forge.plugin_contribution import evaluate_plugin_contributions
from ..forge.replay import compare_replay
from ..ids import content_id
from ..lineage import build_lineage_manifest, detect_stale_lineage
from ..memory.store import ResearchMemory
from ..plugins import (
    PluginAudit,
    PluginDecisionStatus,
    PluginDescriptor,
    PluginUseRecord,
    normalize_plugin_evidence,
)
from ..policy.experiments import select_experiment_route
from ..policy.plugins import PluginSelectionPolicy
from ..policy.promotion import build_research_promotion_packet
from ..provenance import build_research_provenance_manifest
from ..provenance_lineage import ProvenanceLineageReport, verify_provenance_lineage
from ..sentinel.disagreement import detect_disagreements
from ..sentinel.diagnosis import diagnose_disagreement


@dataclass(frozen=True)
class HostPluginResult:
    plugin_id: str
    success: bool
    input_fingerprint: str
    output_fingerprint: str | None = None
    external_result_ref: str | None = None
    failure_class: str | None = None
    contributed_artifact_ids: tuple[str, ...] = ()
    external_attestation: ExternalExecutionAttestation | None = None
    attestation_verification: AttestationVerificationReceipt | None = None


@dataclass(frozen=True)
class RunInput:
    run_kind: LoopKind
    objective: str
    observations: tuple[Any, ...]
    plugin_inventory: tuple[PluginDescriptor, ...]
    plugin_results: tuple[HostPluginResult, ...]
    candidate_profile: Mapping[str, Any]
    baseline_metrics: tuple[tuple[str, float], ...]
    candidate_metrics: tuple[tuple[str, float], ...]
    # stale-aware research lineage (contract-fingerprint staleness)
    contract_fingerprints: tuple[tuple[str, str], ...] = ()
    current_contract_fingerprints: tuple[tuple[str, str], ...] = ()
    # provenance attestation lineage
    source_contract_ids: tuple[str, ...] = ()
    parent_manifest_ids: tuple[str, ...] = ()
    plugin_attestation_policy: PluginAttestationPolicy = PluginAttestationPolicy.OPTIONAL


@dataclass(frozen=True)
class NexusRunInput:
    run_kind: LoopKind
    objective: str
    bundle: Mapping[str, Any]
    contract_snapshot_hash: str
    plugin_inventory: tuple[PluginDescriptor, ...]
    plugin_results: tuple[HostPluginResult, ...]
    candidate_profile: Mapping[str, Any]
    baseline_metrics: tuple[tuple[str, float], ...]
    candidate_metrics: tuple[tuple[str, float], ...]
    current_contract_fingerprints: tuple[tuple[str, str], ...] = ()
    parent_manifest_ids: tuple[str, ...] = ()
    plugin_attestation_policy: PluginAttestationPolicy = PluginAttestationPolicy.OPTIONAL


@dataclass(frozen=True)
class LoopRunResult:
    loop_run_id: str
    status: RunStatus
    plugin_audit: PluginAudit
    plugin_evidence_ids: tuple[str, ...]
    plugin_contribution_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    external_attestation_ids: tuple[str, ...]
    attestation_verification_ids: tuple[str, ...]
    attestation_coverage_gaps: tuple[str, ...]
    disagreements: tuple[DisagreementCase, ...]
    diagnoses: tuple[DisagreementDiagnosis, ...]
    route: ExperimentRouteDecision
    hypothesis: ResearchHypothesis | None
    experiment: ExperimentSpec | None
    result: CandidateImprovement | RejectedHypothesis | DeferredExperiment
    provenance_manifest_id: str | None
    provenance_lineage_report_id: str | None
    promotion_packet: ResearchPromotionPacket | None
    lineage_manifest_id: str
    stale_evidence_report: StaleEvidenceReport
    reused_negative: bool


def _canonical_lineage_ids(label: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if any(not value for value in values):
        raise ValueError(f"{label} contains an empty identifier")
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label} identifier")
    return tuple(sorted(values))


class PrometheusLoop:
    def __init__(self, memory: ResearchMemory, plugin_policy: PluginSelectionPolicy | None = None):
        self.memory = memory
        self.plugin_policy = plugin_policy or PluginSelectionPolicy()

    def run_nexus(self, run_input: NexusRunInput) -> LoopRunResult:
        binding = validate_nexus_bundle(run_input.bundle, run_input.contract_snapshot_hash)
        observations = normalize_nexus_bundle(binding)
        return self.run(
            RunInput(
                run_kind=run_input.run_kind,
                objective=run_input.objective,
                observations=observations,
                plugin_inventory=run_input.plugin_inventory,
                plugin_results=run_input.plugin_results,
                candidate_profile=run_input.candidate_profile,
                baseline_metrics=run_input.baseline_metrics,
                candidate_metrics=run_input.candidate_metrics,
                contract_fingerprints=(("NEXUS", run_input.contract_snapshot_hash),),
                current_contract_fingerprints=run_input.current_contract_fingerprints,
                source_contract_ids=(f"nexus-contract:{binding.contract_snapshot_hash}",),
                parent_manifest_ids=run_input.parent_manifest_ids,
                plugin_attestation_policy=run_input.plugin_attestation_policy,
            )
        )

    @staticmethod
    def _merge_contract_fingerprints(
        rows: tuple[tuple[str, str], ...],
        decisions: tuple,
    ) -> tuple[tuple[str, str], ...]:
        merged: dict[str, str] = {}
        for name, fingerprint in rows:
            if name in merged and merged[name] != fingerprint:
                raise ValueError(f"conflicting contract fingerprint for {name}")
            merged[name] = fingerprint
        for decision in decisions:
            if decision.status is PluginDecisionStatus.SELECTED:
                name = f"plugin:{decision.plugin_id}"
                if name in merged and merged[name] != decision.plugin_descriptor_id:
                    raise ValueError(f"conflicting contract fingerprint for {name}")
                merged[name] = decision.plugin_descriptor_id
        return tuple(sorted(merged.items()))

    @staticmethod
    def _current_contract_map(
        used_contracts: tuple[tuple[str, str], ...],
        overrides: tuple[tuple[str, str], ...],
    ) -> dict[str, str]:
        current = dict(used_contracts)
        seen_overrides: set[str] = set()
        for name, fingerprint in overrides:
            if name in seen_overrides:
                raise ValueError(f"duplicate current contract fingerprint for {name}")
            seen_overrides.add(name)
            current[name] = fingerprint
        return current

    def run(self, run_input: RunInput) -> LoopRunResult:
        source_contract_ids = _canonical_lineage_ids("source contract", run_input.source_contract_ids)
        parent_manifest_ids = _canonical_lineage_ids("parent manifest", run_input.parent_manifest_ids)
        plugin_attestation_policy = PluginAttestationPolicy(run_input.plugin_attestation_policy)
        decisions = self.plugin_policy.select(
            run_input.run_kind,
            run_input.objective,
            run_input.plugin_inventory,
        )
        used_contracts = self._merge_contract_fingerprints(run_input.contract_fingerprints, decisions)
        current_contracts = self._current_contract_map(used_contracts, run_input.current_contract_fingerprints)
        candidate_fingerprint = content_id("candidate-profile", run_input.candidate_profile)
        loop_run_id = content_id(
            "loop",
            {
                "run_kind": run_input.run_kind.value,
                "objective": run_input.objective,
                "observations": [item.artifact_id for item in run_input.observations],
                "plugins": [item.descriptor_id for item in run_input.plugin_inventory],
                "candidate_fingerprint": candidate_fingerprint,
                "source_contract_ids": source_contract_ids,
                "parent_manifest_ids": parent_manifest_ids,
                "plugin_attestation_policy": plugin_attestation_policy.value,
            },
        )
        audit = PluginAudit(loop_run_id=loop_run_id, decisions=decisions)
        result_ids = [item.plugin_id for item in run_input.plugin_results]
        duplicate_result_ids = sorted({plugin_id for plugin_id in result_ids if result_ids.count(plugin_id) > 1})
        if duplicate_result_ids:
            raise ValueError(f"duplicate host plugin result for: {', '.join(duplicate_result_ids)}")
        results_by_plugin = {item.plugin_id: item for item in run_input.plugin_results}
        selected = [item for item in decisions if item.status is PluginDecisionStatus.SELECTED]
        for decision in selected:
            host = results_by_plugin.get(decision.plugin_id)
            if host is None:
                raise ValueError(f"selected plugin {decision.plugin_id} was not executed by the host")
            if host.success:
                use = PluginUseRecord.completed(
                    loop_run_id=loop_run_id,
                    plugin_id=host.plugin_id,
                    input_fingerprint=host.input_fingerprint,
                    output_fingerprint=host.output_fingerprint,
                    external_result_ref=host.external_result_ref,
                    contributed_artifact_ids=host.contributed_artifact_ids,
                )
            else:
                use = PluginUseRecord.failed(
                    loop_run_id=loop_run_id,
                    plugin_id=host.plugin_id,
                    input_fingerprint=host.input_fingerprint,
                    failure_class=host.failure_class or "unspecified_failure",
                )
            audit = audit.record_use(use)

        plugin_evidence = normalize_plugin_evidence(audit, run_input.plugin_inventory)
        plugin_contributions = evaluate_plugin_contributions(plugin_evidence)

        external_attestations: list[ExternalExecutionAttestation] = []
        attestation_receipts: list[AttestationVerificationReceipt] = []
        attestation_coverage_gaps: list[str] = []
        strict_attestation_failure = False
        for evidence in plugin_evidence:
            host = results_by_plugin[evidence.plugin_id]
            attestation = host.external_attestation
            receipt = host.attestation_verification
            if (attestation is None) != (receipt is None):
                raise ValueError(
                    f"external attestation and verification receipt must be supplied together for {evidence.plugin_id}"
                )
            if attestation is None:
                attestation_coverage_gaps.append(evidence.plugin_id)
                if plugin_attestation_policy is PluginAttestationPolicy.REQUIRE_VERIFIED:
                    strict_attestation_failure = True
                continue
            validate_external_attestation_binding(evidence.artifact_id, attestation, receipt)
            external_attestations.append(attestation)
            attestation_receipts.append(receipt)
            if plugin_attestation_policy is PluginAttestationPolicy.REQUIRE_VERIFIED and not receipt.verified:
                strict_attestation_failure = True

        degraded = any(d.status is PluginDecisionStatus.UNAVAILABLE and "deep_research" in d.capabilities for d in decisions)
        degraded = degraded or any(use.status is PluginDecisionStatus.FAILED for use in audit.uses)
        degraded = degraded or strict_attestation_failure
        requested_status = RunStatus.DEGRADED_RESEARCH if degraded else RunStatus.RESEARCH_COMPLETE
        status = audit.finalize(requested_status)

        disagreements = detect_disagreements(run_input.observations)
        if not disagreements:
            raise ValueError("no disagreement case was detected for this v0.1 research loop")
        diagnoses = tuple(diagnose_disagreement(case, run_input.observations) for case in disagreements)
        plugin_evidence_ids = tuple(item.artifact_id for item in plugin_evidence)
        plugin_contribution_ids = tuple(item.artifact_id for item in plugin_contributions)
        observation_ids = tuple(item.artifact_id for item in run_input.observations)
        external_attestation_ids = tuple(sorted(item.artifact_id for item in external_attestations))
        attestation_verification_ids = tuple(sorted(item.artifact_id for item in attestation_receipts))
        selected_plugin_descriptor_ids = tuple(
            item.plugin_descriptor_id
            for item in decisions
            if item.status is PluginDecisionStatus.SELECTED
        )

        for artifact in (
            *run_input.observations,
            *plugin_evidence,
            *plugin_contributions,
            *external_attestations,
            *attestation_receipts,
            *disagreements,
            *diagnoses,
            audit,
        ):
            self.memory.append(artifact)

        preflight_lineage = build_lineage_manifest(
            root_artifact_id=audit.artifact_id,
            artifact_ids=(
                *observation_ids,
                *plugin_evidence_ids,
                *plugin_contribution_ids,
                *external_attestation_ids,
                *attestation_verification_ids,
                *(item.artifact_id for item in disagreements),
                *(item.artifact_id for item in diagnoses),
                audit.artifact_id,
            ),
            predecessor_ids=tuple(
                sorted(
                    {
                        *(item.artifact_id for item in disagreements),
                        *(item.artifact_id for item in diagnoses),
                    }
                )
            ),
            contract_fingerprints=used_contracts,
        )
        preflight_stale_report = detect_stale_lineage(preflight_lineage, current_contracts)
        route = select_experiment_route(
            cases=disagreements,
            diagnoses=diagnoses,
            preflight_lineage=preflight_lineage,
            stale_report=preflight_stale_report,
        )
        for artifact in (preflight_lineage, preflight_stale_report, route):
            self.memory.append(artifact)

        if route.action is not ExperimentRouteAction.RUN_REPLAY:
            if route.action is ExperimentRouteAction.ABSTAIN_SPECIALIZATION:
                rerun_condition = (
                    "Revisit only if sibling authority contracts change or a new shared-evidence disagreement appears."
                )
            else:
                rerun_condition = (
                    "Rerun only after bound contract fingerprints and source availability/health are fresh at decision time."
                )
            deferred = DeferredExperiment(
                route_decision_id=route.artifact_id,
                case_id=route.case_id,
                diagnosis_id=route.diagnosis_id,
                reason_code=route.reason_code,
                evidence_ids=tuple(
                    sorted(
                        {
                            *route.evidence_ids,
                            preflight_lineage.artifact_id,
                            preflight_stale_report.artifact_id,
                        }
                    )
                ),
                rerun_condition=rerun_condition,
            )
            self.memory.append(deferred)
            lineage = build_lineage_manifest(
                root_artifact_id=deferred.artifact_id,
                artifact_ids=tuple(
                    sorted(
                        {
                            *observation_ids,
                            *plugin_evidence_ids,
                            *plugin_contribution_ids,
                            *external_attestation_ids,
                            *attestation_verification_ids,
                            *(item.artifact_id for item in disagreements),
                            *(item.artifact_id for item in diagnoses),
                            audit.artifact_id,
                            preflight_lineage.artifact_id,
                            preflight_stale_report.artifact_id,
                            route.artifact_id,
                            deferred.artifact_id,
                        }
                    )
                ),
                predecessor_ids=(route.artifact_id, preflight_lineage.artifact_id),
                contract_fingerprints=used_contracts,
            )
            stale_report = detect_stale_lineage(lineage, current_contracts)
            self.memory.append(lineage)
            self.memory.append(stale_report)
            return LoopRunResult(
                loop_run_id=loop_run_id,
                status=status,
                plugin_audit=audit,
                plugin_evidence_ids=plugin_evidence_ids,
                plugin_contribution_ids=plugin_contribution_ids,
                observation_ids=observation_ids,
                external_attestation_ids=external_attestation_ids,
                attestation_verification_ids=attestation_verification_ids,
                attestation_coverage_gaps=tuple(sorted(attestation_coverage_gaps)),
                disagreements=disagreements,
                diagnoses=diagnoses,
                route=route,
                hypothesis=None,
                experiment=None,
                result=deferred,
                provenance_manifest_id=None,
                provenance_lineage_report_id=None,
                promotion_packet=None,
                lineage_manifest_id=lineage.artifact_id,
                stale_evidence_report=stale_report,
                reused_negative=False,
            )

        case_by_id = {case.artifact_id: case for case in disagreements}
        primary = case_by_id[route.case_id]
        hypothesis = hypothesis_from_case(primary)
        experiment = ExperimentSpec(
            hypothesis_id=hypothesis.artifact_id,
            decision_instant=primary.decision_instant,
            checks=route.required_checks,
            candidate_fingerprint=candidate_fingerprint,
            routing_context_id=route.artifact_id,
        )
        self.memory.append(hypothesis)
        self.memory.append(experiment)

        if self.memory.has_negative(experiment.artifact_id):
            prior = self.memory.negative_for(experiment.artifact_id)
            lineage = build_lineage_manifest(
                root_artifact_id=prior.artifact_id,
                artifact_ids=tuple(
                    sorted(
                        {
                            *observation_ids,
                            *plugin_evidence_ids,
                            *plugin_contribution_ids,
                            *external_attestation_ids,
                            *attestation_verification_ids,
                            *(item.artifact_id for item in disagreements),
                            *(item.artifact_id for item in diagnoses),
                            audit.artifact_id,
                            preflight_lineage.artifact_id,
                            preflight_stale_report.artifact_id,
                            route.artifact_id,
                            hypothesis.artifact_id,
                            experiment.artifact_id,
                            prior.artifact_id,
                        }
                    )
                ),
                predecessor_ids=(route.artifact_id, primary.artifact_id, hypothesis.artifact_id, experiment.artifact_id),
                contract_fingerprints=used_contracts,
            )
            stale_report = detect_stale_lineage(lineage, current_contracts)
            self.memory.append(lineage)
            self.memory.append(stale_report)
            return LoopRunResult(
                loop_run_id=loop_run_id,
                status=status,
                plugin_audit=audit,
                plugin_evidence_ids=plugin_evidence_ids,
                plugin_contribution_ids=plugin_contribution_ids,
                observation_ids=observation_ids,
                external_attestation_ids=external_attestation_ids,
                attestation_verification_ids=attestation_verification_ids,
                attestation_coverage_gaps=tuple(sorted(attestation_coverage_gaps)),
                disagreements=disagreements,
                diagnoses=diagnoses,
                route=route,
                hypothesis=hypothesis,
                experiment=experiment,
                result=prior,
                provenance_manifest_id=None,
                provenance_lineage_report_id=None,
                promotion_packet=None,
                lineage_manifest_id=lineage.artifact_id,
                stale_evidence_report=stale_report,
                reused_negative=True,
            )

        adversarial = run_adversarial(experiment, {}, run_input.candidate_profile)
        self.memory.append(adversarial)
        result = compare_replay(
            experiment,
            baseline_metrics=dict(run_input.baseline_metrics),
            candidate_metrics=dict(run_input.candidate_metrics),
            adversarial_report=adversarial,
        )
        self.memory.append(result)
        lineage = build_lineage_manifest(
            root_artifact_id=result.artifact_id,
            artifact_ids=tuple(
                sorted(
                    {
                        *observation_ids,
                        *plugin_evidence_ids,
                        *plugin_contribution_ids,
                        *external_attestation_ids,
                        *attestation_verification_ids,
                        *(item.artifact_id for item in disagreements),
                        *(item.artifact_id for item in diagnoses),
                        audit.artifact_id,
                        preflight_lineage.artifact_id,
                        preflight_stale_report.artifact_id,
                        route.artifact_id,
                        hypothesis.artifact_id,
                        experiment.artifact_id,
                        adversarial.artifact_id,
                        result.artifact_id,
                    }
                )
            ),
            predecessor_ids=(
                route.artifact_id,
                primary.artifact_id,
                hypothesis.artifact_id,
                experiment.artifact_id,
                adversarial.artifact_id,
            ),
            contract_fingerprints=used_contracts,
        )
        stale_report = detect_stale_lineage(lineage, current_contracts)
        self.memory.append(lineage)
        self.memory.append(stale_report)

        # Provenance is built only for a promotion-eligible result: complete run,
        # engineering pass, and clean stale-aware lineage.
        provenance_manifest = None
        if (
            status is RunStatus.RESEARCH_COMPLETE
            and not stale_report.is_stale
            and isinstance(result, CandidateImprovement)
            and result.status is CandidateStatus.PROMETHEUS_ENGINEERING_PASS
        ):
            provenance_manifest = build_research_provenance_manifest(
                loop_run_id=loop_run_id,
                experiment_id=experiment.artifact_id,
                candidate_id=result.artifact_id,
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
            self.memory.append(provenance_manifest)

        provenance_lineage_report: ProvenanceLineageReport | None = None
        if provenance_manifest is not None:
            provenance_lineage_report = verify_provenance_lineage(self.memory, provenance_manifest.artifact_id)
            self.memory.append(provenance_lineage_report)

        promotion_packet = build_research_promotion_packet(
            run_status=status,
            result=result,
            plugin_evidence_ids=plugin_evidence_ids,
            plugin_contribution_ids=plugin_contribution_ids,
            lineage_manifest_id=lineage.artifact_id,
            stale_report=stale_report,
            provenance_manifest=provenance_manifest,
            provenance_lineage_report=provenance_lineage_report,
            loop_run_id=loop_run_id,
            selected_plugin_descriptor_ids=selected_plugin_descriptor_ids,
            observation_ids=observation_ids,
            source_contract_ids=source_contract_ids,
            parent_manifest_ids=parent_manifest_ids,
            external_attestation_ids=external_attestation_ids,
            attestation_verification_ids=attestation_verification_ids,
            plugin_attestation_policy=plugin_attestation_policy,
        )
        if promotion_packet is not None:
            self.memory.append(promotion_packet)
        return LoopRunResult(
            loop_run_id=loop_run_id,
            status=status,
            plugin_audit=audit,
            plugin_evidence_ids=plugin_evidence_ids,
            plugin_contribution_ids=plugin_contribution_ids,
            observation_ids=observation_ids,
            external_attestation_ids=external_attestation_ids,
            attestation_verification_ids=attestation_verification_ids,
            attestation_coverage_gaps=tuple(sorted(attestation_coverage_gaps)),
            disagreements=disagreements,
            diagnoses=diagnoses,
            route=route,
            hypothesis=hypothesis,
            experiment=experiment,
            result=result,
            provenance_manifest_id=provenance_manifest.artifact_id if provenance_manifest else None,
            provenance_lineage_report_id=provenance_lineage_report.artifact_id if provenance_lineage_report else None,
            promotion_packet=promotion_packet,
            lineage_manifest_id=lineage.artifact_id,
            stale_evidence_report=stale_report,
            reused_negative=False,
        )
