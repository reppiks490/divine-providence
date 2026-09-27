from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .ids import content_id
from .attestation import PluginAttestationPolicy


class LoopKind(str, Enum):
    SENTINEL = "SENTINEL"
    FORGE = "FORGE"
    ASCENSION = "ASCENSION"


class RunStatus(str, Enum):
    RESEARCH_COMPLETE = "RESEARCH_COMPLETE"
    DEGRADED_RESEARCH = "DEGRADED_RESEARCH"
    RESEARCH_FAILED = "RESEARCH_FAILED"


class CandidateStatus(str, Enum):
    RESEARCH_ONLY = "RESEARCH_ONLY"
    PROMETHEUS_ENGINEERING_PASS = "PROMETHEUS_ENGINEERING_PASS"


class PluginContributionOutcome(str, Enum):
    UNIQUE = "UNIQUE"
    SHARED = "SHARED"
    UNIQUE_AND_SHARED = "UNIQUE_AND_SHARED"
    NO_ATTRIBUTED_ARTIFACTS = "NO_ATTRIBUTED_ARTIFACTS"
    FAILED = "FAILED"


class PromotionStatus(str, Enum):
    READY_FOR_DAEDALUS_REVIEW = "READY_FOR_DAEDALUS_REVIEW"


class DisagreementCause(str, Enum):
    EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"
    AVAILABILITY_MISMATCH = "AVAILABILITY_MISMATCH"
    REPRESENTATION_MISMATCH = "REPRESENTATION_MISMATCH"
    SOURCE_HEALTH_ISSUE = "SOURCE_HEALTH_ISSUE"
    REGIME_BOUNDARY = "REGIME_BOUNDARY"
    MODEL_BLIND_SPOT = "MODEL_BLIND_SPOT"
    INTENTIONAL_SPECIALIZATION = "INTENTIONAL_SPECIALIZATION"
    IRREDUCIBLE_AMBIGUITY = "IRREDUCIBLE_AMBIGUITY"


class ExperimentRouteAction(str, Enum):
    RUN_REPLAY = "RUN_REPLAY"
    DEFER_FRESH_EVIDENCE = "DEFER_FRESH_EVIDENCE"
    ABSTAIN_SPECIALIZATION = "ABSTAIN_SPECIALIZATION"


class ResearchPriorityBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass(frozen=True)
class ObservationEnvelope:
    sibling: str
    decision_instant: str
    availability_state: str
    evidence_tier: str
    dimensions: tuple[tuple[str, str], ...]
    source_ref: str

    @property
    def artifact_id(self) -> str:
        return content_id("observation", self)




@dataclass(frozen=True)
class FailureCase:
    failure_type: str
    source_system: str
    expected_contract_hash: str
    observed_contract_hash: str
    decision_instant: str
    details: str

    @property
    def artifact_id(self) -> str:
        return content_id("failure", self)


@dataclass(frozen=True)
class DisagreementCase:
    decision_instant: str
    dimension: str
    observation_ids: tuple[str, ...]
    values: tuple[str, ...]
    disagreement_type: str

    @property
    def artifact_id(self) -> str:
        return content_id("disagreement", self)


@dataclass(frozen=True)
class DisagreementDiagnosis:
    case_id: str
    cause: DisagreementCause
    evidence_ids: tuple[str, ...]
    rationale: str

    @property
    def artifact_id(self) -> str:
        return content_id("disagreement-diagnosis", self)


@dataclass(frozen=True)
class ExperimentRouteDecision:
    case_id: str
    diagnosis_id: str
    action: ExperimentRouteAction
    priority_band: ResearchPriorityBand
    reason_code: str
    required_checks: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    preflight_lineage_id: str
    stale_report_id: str

    @property
    def artifact_id(self) -> str:
        return content_id("experiment-route", self)


@dataclass(frozen=True)
class DeferredExperiment:
    route_decision_id: str
    case_id: str
    diagnosis_id: str
    reason_code: str
    evidence_ids: tuple[str, ...]
    rerun_condition: str

    @property
    def artifact_id(self) -> str:
        return content_id("deferred-experiment", self)


@dataclass(frozen=True)
class ResearchHypothesis:
    case_id: str
    family: str
    claim: str
    falsifier: str

    @property
    def artifact_id(self) -> str:
        return content_id("hypothesis", self)


@dataclass(frozen=True)
class ExperimentSpec:
    hypothesis_id: str
    decision_instant: str
    checks: tuple[str, ...]
    candidate_fingerprint: str = "candidate:default"
    routing_context_id: str = "routing:default"

    @property
    def artifact_id(self) -> str:
        return content_id("experiment", self)


@dataclass(frozen=True)
class ReplayResult:
    experiment_id: str
    baseline_metrics: tuple[tuple[str, float], ...]
    candidate_metrics: tuple[tuple[str, float], ...]
    deterministic: bool
    passed_guardrails: bool

    @property
    def artifact_id(self) -> str:
        return content_id("replay", self)


@dataclass(frozen=True)
class AdversarialReport:
    experiment_id: str
    passed: bool
    failed_checks: tuple[str, ...]
    details: tuple[tuple[str, str], ...]

    @property
    def artifact_id(self) -> str:
        return content_id("adversarial", self)


@dataclass(frozen=True)
class CandidateImprovement:
    experiment_id: str
    status: CandidateStatus
    evidence_ids: tuple[str, ...]
    summary: str

    @property
    def artifact_id(self) -> str:
        return content_id("candidate", self)


@dataclass(frozen=True)
class RejectedHypothesis:
    experiment_id: str
    reason: str
    evidence_ids: tuple[str, ...]

    @property
    def artifact_id(self) -> str:
        return content_id("rejected", self)

@dataclass(frozen=True)
class PluginContributionReport:
    loop_run_id: str
    plugin_id: str
    plugin_evidence_id: str
    outcome: PluginContributionOutcome
    unique_artifact_ids: tuple[str, ...] = ()
    shared_artifact_ids: tuple[str, ...] = ()
    failure_class: str | None = None

    @property
    def artifact_id(self) -> str:
        return content_id("plugin-contribution", self)


def _canonical_id_tuple(
    name: str,
    values: tuple[str, ...],
    *,
    required: bool = False,
    prefix: str | None = None,
) -> tuple[str, ...]:
    if required and not values:
        raise ValueError(f"{name} requires at least one identifier")
    if any(not value for value in values):
        raise ValueError(f"{name} contains an empty identifier")
    if prefix is not None and any(not value.startswith(prefix) for value in values):
        raise ValueError(f"{name} contains an identifier outside the {prefix} namespace")
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate identifier in {name}")
    return tuple(sorted(values))


@dataclass(frozen=True)
class ResearchProvenanceManifest:
    loop_run_id: str
    experiment_id: str
    candidate_id: str
    selected_plugin_descriptor_ids: tuple[str, ...]
    plugin_evidence_ids: tuple[str, ...]
    plugin_contribution_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    source_contract_ids: tuple[str, ...] = ()
    parent_manifest_ids: tuple[str, ...] = ()
    external_attestation_ids: tuple[str, ...] = ()
    attestation_verification_ids: tuple[str, ...] = ()
    plugin_attestation_policy: PluginAttestationPolicy = PluginAttestationPolicy.OPTIONAL

    def __post_init__(self) -> None:
        scalar_prefixes = {
            "loop_run_id": "loop:",
            "experiment_id": "experiment:",
            "candidate_id": "candidate:",
        }
        for name, prefix in scalar_prefixes.items():
            value = getattr(self, name)
            if not value:
                raise ValueError(f"{name} must be non-empty")
            if not value.startswith(prefix):
                raise ValueError(f"{name} must use the {prefix} namespace")

        try:
            policy = PluginAttestationPolicy(self.plugin_attestation_policy)
        except ValueError as exc:
            raise ValueError("unsupported plugin_attestation_policy") from exc
        object.__setattr__(self, "plugin_attestation_policy", policy)

        collections = {
            "selected_plugin_descriptor_ids": (self.selected_plugin_descriptor_ids, "plugin:"),
            "plugin_evidence_ids": (self.plugin_evidence_ids, "plugin-evidence:"),
            "plugin_contribution_ids": (self.plugin_contribution_ids, "plugin-contribution:"),
            "observation_ids": (self.observation_ids, "observation:"),
            "source_contract_ids": (self.source_contract_ids, None),
            "parent_manifest_ids": (self.parent_manifest_ids, "research-provenance:"),
            "external_attestation_ids": (self.external_attestation_ids, "external-attestation:"),
            "attestation_verification_ids": (self.attestation_verification_ids, "attestation-verification:"),
        }
        for name, (values, prefix) in collections.items():
            object.__setattr__(
                self,
                name,
                _canonical_id_tuple(
                    name,
                    values,
                    required=name == "observation_ids",
                    prefix=prefix,
                ),
            )

        counts = (
            len(self.selected_plugin_descriptor_ids),
            len(self.plugin_evidence_ids),
            len(self.plugin_contribution_ids),
        )
        if len(set(counts)) != 1:
            raise ValueError("plugin provenance cardinality must match selected descriptors, evidence, and contributions")

        attestation_count = len(self.external_attestation_ids)
        receipt_count = len(self.attestation_verification_ids)
        if attestation_count != receipt_count:
            raise ValueError("attestation and receipt cardinality must match")
        selected_count = len(self.selected_plugin_descriptor_ids)
        if attestation_count > selected_count:
            raise ValueError("attestation coverage exceeds selected plugin cardinality")
        if policy is PluginAttestationPolicy.REQUIRE_VERIFIED and attestation_count != selected_count:
            raise ValueError("strict attestation cardinality must match selected plugins")

    @property
    def artifact_id(self) -> str:
        return content_id("research-provenance", self)

@dataclass(frozen=True)
class ResearchLineageManifest:
    root_artifact_id: str
    artifact_ids: tuple[str, ...]
    predecessor_ids: tuple[str, ...]
    contract_fingerprints: tuple[tuple[str, str], ...]

    @property
    def artifact_id(self) -> str:
        return content_id("lineage-manifest", self)


@dataclass(frozen=True)
class StaleEvidenceReport:
    lineage_manifest_id: str
    contract_mismatches: tuple[tuple[str, str, str], ...]

    @property
    def is_stale(self) -> bool:
        return bool(self.contract_mismatches)

    @property
    def artifact_id(self) -> str:
        return content_id("stale-evidence", self)


@dataclass(frozen=True)
class ResearchPromotionPacket:
    candidate_id: str
    target_system: str
    status: PromotionStatus
    evidence_ids: tuple[str, ...]
    # All three bindings are mandatory; the empty defaults only allow keyword
    # construction and are rejected by __post_init__.
    lineage_manifest_id: str = ""
    provenance_manifest_id: str = ""
    provenance_lineage_report_id: str = ""
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.target_system != "DAEDALUS":
            raise ValueError("research promotion target must be DAEDALUS")
        if self.status is not PromotionStatus.READY_FOR_DAEDALUS_REVIEW:
            raise ValueError("unsupported research promotion status")
        if self.production_authorized:
            raise ValueError("PROMETHEUS cannot grant production authorization")
        if not self.evidence_ids:
            raise ValueError("research promotion requires evidence")
        if not self.provenance_manifest_id.startswith("research-provenance:"):
            raise ValueError("research promotion requires a provenance manifest")
        if not self.provenance_lineage_report_id.startswith("provenance-lineage:"):
            raise ValueError("research promotion requires a provenance lineage report")
        if self.provenance_manifest_id not in self.evidence_ids:
            raise ValueError("research promotion evidence must include the provenance manifest")
        if self.provenance_lineage_report_id not in self.evidence_ids:
            raise ValueError("research promotion evidence must include the lineage report")
        if not self.lineage_manifest_id:
            raise ValueError("research promotion requires lineage manifest")

    @property
    def artifact_id(self) -> str:
        return content_id("promotion-packet", self)

