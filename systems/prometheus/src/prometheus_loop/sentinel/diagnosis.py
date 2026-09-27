from __future__ import annotations

from ..contracts import (
    DisagreementCase,
    DisagreementCause,
    DisagreementDiagnosis,
    ObservationEnvelope,
)


_ROLE_SPECIALIZATION_DIMENSIONS = {
    "advisory_only",
    "candidate_kind",
    "contract",
    "data_plane",
    "evidence_tier",
    "frame_hash",
    "microstructure_truth",
    "production_authorized",
    "purpose",
    "schema",
    "status",
}

_SHARED_CONTEXT_PREFIXES = ("factor:", "quality:", "ood:")


def diagnose_disagreement(
    case: DisagreementCase,
    observations: tuple[ObservationEnvelope, ...],
) -> DisagreementDiagnosis:
    by_id = {item.artifact_id: item for item in observations}
    missing = tuple(identifier for identifier in case.observation_ids if identifier not in by_id)
    if missing:
        raise ValueError(f"missing observation for disagreement diagnosis: {', '.join(missing)}")

    involved = tuple(by_id[identifier] for identifier in case.observation_ids)
    availability_states = {item.availability_state for item in involved}
    if len(availability_states) > 1:
        cause = DisagreementCause.AVAILABILITY_MISMATCH
        rationale = "participants disagree under different availability states"
    elif case.dimension.startswith("source_health:"):
        cause = DisagreementCause.SOURCE_HEALTH_ISSUE
        rationale = "disagreement is directly expressed in source-health evidence"
    elif case.dimension.startswith("representation:"):
        cause = DisagreementCause.REPRESENTATION_MISMATCH
        rationale = "disagreement is directly expressed in representation metadata"
    elif case.dimension == "regime" or case.dimension.startswith("regime:"):
        cause = DisagreementCause.REGIME_BOUNDARY
        rationale = "disagreement is directly expressed in regime classification"
    elif case.dimension in _ROLE_SPECIALIZATION_DIMENSIONS:
        cause = DisagreementCause.INTENTIONAL_SPECIALIZATION
        rationale = "dimension is role-specific by sibling contract and is not expected to converge"
    elif case.dimension.startswith(_SHARED_CONTEXT_PREFIXES):
        cause = DisagreementCause.EVIDENCE_MISMATCH
        rationale = "shared NEXUS context differs across sibling projections"
    else:
        cause = DisagreementCause.IRREDUCIBLE_AMBIGUITY
        rationale = "available evidence does not justify a narrower root-cause claim"

    return DisagreementDiagnosis(
        case_id=case.artifact_id,
        cause=cause,
        evidence_ids=tuple(sorted(case.observation_ids)),
        rationale=rationale,
    )
