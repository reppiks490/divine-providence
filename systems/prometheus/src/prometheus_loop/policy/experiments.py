from __future__ import annotations

from ..contracts import (
    DisagreementCase,
    DisagreementCause,
    DisagreementDiagnosis,
    ExperimentRouteAction,
    ExperimentRouteDecision,
    ResearchLineageManifest,
    ResearchPriorityBand,
    StaleEvidenceReport,
)


_CORE_REPLAY_CHECKS = ("leakage", "missingness", "reproducibility")


def _checks(*extra: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*_CORE_REPLAY_CHECKS, *extra)))


_ROUTE_BY_CAUSE = {
    DisagreementCause.EVIDENCE_MISMATCH: (
        ExperimentRouteAction.RUN_REPLAY,
        ResearchPriorityBand.HIGH,
        "REDUCIBLE_EVIDENCE_MISMATCH",
        _checks("ablation", "perturbation"),
    ),
    DisagreementCause.REPRESENTATION_MISMATCH: (
        ExperimentRouteAction.RUN_REPLAY,
        ResearchPriorityBand.HIGH,
        "REPRESENTATION_SENSITIVITY_PROBE",
        _checks("ablation", "perturbation"),
    ),
    DisagreementCause.MODEL_BLIND_SPOT: (
        ExperimentRouteAction.RUN_REPLAY,
        ResearchPriorityBand.HIGH,
        "MODEL_BLIND_SPOT_PROBE",
        _checks("ablation"),
    ),
    DisagreementCause.REGIME_BOUNDARY: (
        ExperimentRouteAction.RUN_REPLAY,
        ResearchPriorityBand.MEDIUM,
        "REGIME_BOUNDARY_PROBE",
        _checks("perturbation"),
    ),
    DisagreementCause.IRREDUCIBLE_AMBIGUITY: (
        ExperimentRouteAction.RUN_REPLAY,
        ResearchPriorityBand.MEDIUM,
        "AMBIGUITY_REDUCTION_PROBE",
        _checks("ablation", "perturbation"),
    ),
    DisagreementCause.AVAILABILITY_MISMATCH: (
        ExperimentRouteAction.DEFER_FRESH_EVIDENCE,
        ResearchPriorityBand.LOW,
        "AVAILABILITY_NOT_REPLAY_ELIGIBLE",
        (),
    ),
    DisagreementCause.SOURCE_HEALTH_ISSUE: (
        ExperimentRouteAction.DEFER_FRESH_EVIDENCE,
        ResearchPriorityBand.LOW,
        "SOURCE_HEALTH_NOT_REPLAY_ELIGIBLE",
        (),
    ),
    DisagreementCause.INTENTIONAL_SPECIALIZATION: (
        ExperimentRouteAction.ABSTAIN_SPECIALIZATION,
        ResearchPriorityBand.NONE,
        "HEALTHY_ROLE_SPECIALIZATION",
        (),
    ),
}

_ACTION_RANK = {
    ExperimentRouteAction.RUN_REPLAY: 0,
    ExperimentRouteAction.DEFER_FRESH_EVIDENCE: 1,
    ExperimentRouteAction.ABSTAIN_SPECIALIZATION: 2,
}
_PRIORITY_RANK = {
    ResearchPriorityBand.HIGH: 0,
    ResearchPriorityBand.MEDIUM: 1,
    ResearchPriorityBand.LOW: 2,
    ResearchPriorityBand.NONE: 3,
}


def select_experiment_route(
    *,
    cases: tuple[DisagreementCase, ...],
    diagnoses: tuple[DisagreementDiagnosis, ...],
    preflight_lineage: ResearchLineageManifest,
    stale_report: StaleEvidenceReport,
) -> ExperimentRouteDecision:
    if stale_report.lineage_manifest_id != preflight_lineage.artifact_id:
        raise ValueError("staleness report does not match preflight lineage")
    case_by_id = {case.artifact_id: case for case in cases}
    if not diagnoses:
        raise ValueError("experiment routing requires at least one diagnosis")
    for diagnosis in diagnoses:
        if diagnosis.case_id not in case_by_id:
            raise ValueError(f"diagnosis references unknown disagreement case {diagnosis.case_id}")

    ranked = []
    for diagnosis in diagnoses:
        action, band, reason, checks = _ROUTE_BY_CAUSE[diagnosis.cause]
        ranked.append((
            _ACTION_RANK[action],
            _PRIORITY_RANK[band],
            diagnosis.artifact_id,
            diagnosis,
            action,
            band,
            reason,
            checks,
        ))
    _, _, _, diagnosis, action, band, reason, checks = min(ranked)
    case = case_by_id[diagnosis.case_id]

    if stale_report.is_stale:
        action = ExperimentRouteAction.DEFER_FRESH_EVIDENCE
        band = ResearchPriorityBand.LOW
        reason = "STALE_CONTRACT_LINEAGE"
        checks = ()

    return ExperimentRouteDecision(
        case_id=case.artifact_id,
        diagnosis_id=diagnosis.artifact_id,
        action=action,
        priority_band=band,
        reason_code=reason,
        required_checks=checks,
        evidence_ids=tuple(sorted(set((*diagnosis.evidence_ids, case.artifact_id, diagnosis.artifact_id)))),
        preflight_lineage_id=preflight_lineage.artifact_id,
        stale_report_id=stale_report.artifact_id,
    )
