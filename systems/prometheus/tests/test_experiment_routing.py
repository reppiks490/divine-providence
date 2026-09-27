from prometheus_loop.contracts import (
    DisagreementCase,
    DisagreementCause,
    DisagreementDiagnosis,
    ExperimentRouteAction,
    ResearchLineageManifest,
    ResearchPriorityBand,
    StaleEvidenceReport,
)
from prometheus_loop.policy.experiments import select_experiment_route


def _case(name: str, dimension: str) -> DisagreementCase:
    return DisagreementCase(
        decision_instant="160",
        dimension=dimension,
        observation_ids=(f"observation:{name}:a", f"observation:{name}:b"),
        values=("a", "b"),
        disagreement_type="VALUE",
    )


def _diagnosis(case: DisagreementCase, cause: DisagreementCause) -> DisagreementDiagnosis:
    return DisagreementDiagnosis(
        case_id=case.artifact_id,
        cause=cause,
        evidence_ids=case.observation_ids,
        rationale=f"fixture:{cause.value}",
    )


def _lineage() -> ResearchLineageManifest:
    return ResearchLineageManifest(
        root_artifact_id="audit:fixture",
        artifact_ids=("observation:a",),
        predecessor_ids=(),
        contract_fingerprints=(("NEXUS", "nexus-v1"),),
    )


def _fresh(lineage: ResearchLineageManifest) -> StaleEvidenceReport:
    return StaleEvidenceReport(lineage_manifest_id=lineage.artifact_id, contract_mismatches=())


def test_actionable_evidence_mismatch_beats_intentional_specialization():
    specialization = _case("special", "contract")
    actionable = _case("evidence", "factor:tech")
    lineage = _lineage()
    route = select_experiment_route(
        cases=(specialization, actionable),
        diagnoses=(
            _diagnosis(specialization, DisagreementCause.INTENTIONAL_SPECIALIZATION),
            _diagnosis(actionable, DisagreementCause.EVIDENCE_MISMATCH),
        ),
        preflight_lineage=lineage,
        stale_report=_fresh(lineage),
    )
    assert route.case_id == actionable.artifact_id
    assert route.action is ExperimentRouteAction.RUN_REPLAY
    assert route.priority_band is ResearchPriorityBand.HIGH
    assert route.reason_code == "REDUCIBLE_EVIDENCE_MISMATCH"


def test_stale_lineage_vetoes_replay_even_for_actionable_disagreement():
    case = _case("evidence", "factor:tech")
    lineage = _lineage()
    stale = StaleEvidenceReport(
        lineage_manifest_id=lineage.artifact_id,
        contract_mismatches=(("NEXUS", "nexus-v1", "nexus-v2"),),
    )
    route = select_experiment_route(
        cases=(case,),
        diagnoses=(_diagnosis(case, DisagreementCause.EVIDENCE_MISMATCH),),
        preflight_lineage=lineage,
        stale_report=stale,
    )
    assert route.action is ExperimentRouteAction.DEFER_FRESH_EVIDENCE
    assert route.reason_code == "STALE_CONTRACT_LINEAGE"
    assert route.required_checks == ()


def test_source_health_issue_waits_for_fresh_evidence():
    case = _case("health", "source_health:healthy_fraction")
    lineage = _lineage()
    route = select_experiment_route(
        cases=(case,),
        diagnoses=(_diagnosis(case, DisagreementCause.SOURCE_HEALTH_ISSUE),),
        preflight_lineage=lineage,
        stale_report=_fresh(lineage),
    )
    assert route.action is ExperimentRouteAction.DEFER_FRESH_EVIDENCE
    assert route.reason_code == "SOURCE_HEALTH_NOT_REPLAY_ELIGIBLE"


def test_ambiguity_uses_bounded_information_gain_replay_without_claiming_cause():
    case = _case("ambiguous", "direction")
    lineage = _lineage()
    route = select_experiment_route(
        cases=(case,),
        diagnoses=(_diagnosis(case, DisagreementCause.IRREDUCIBLE_AMBIGUITY),),
        preflight_lineage=lineage,
        stale_report=_fresh(lineage),
    )
    assert route.action is ExperimentRouteAction.RUN_REPLAY
    assert route.priority_band is ResearchPriorityBand.MEDIUM
    assert route.reason_code == "AMBIGUITY_REDUCTION_PROBE"
    assert "reproducibility" in route.required_checks


def test_route_is_deterministic_when_case_order_changes():
    first = _case("one", "factor:tech")
    second = _case("two", "representation:family")
    diagnoses = (
        _diagnosis(first, DisagreementCause.EVIDENCE_MISMATCH),
        _diagnosis(second, DisagreementCause.REPRESENTATION_MISMATCH),
    )
    lineage = _lineage()
    a = select_experiment_route(
        cases=(first, second),
        diagnoses=diagnoses,
        preflight_lineage=lineage,
        stale_report=_fresh(lineage),
    )
    b = select_experiment_route(
        cases=(second, first),
        diagnoses=tuple(reversed(diagnoses)),
        preflight_lineage=lineage,
        stale_report=_fresh(lineage),
    )
    assert a.artifact_id == b.artifact_id


def test_all_replay_routes_keep_nonnegotiable_core_guardrails():
    lineage = _lineage()
    for cause, dimension in (
        (DisagreementCause.REPRESENTATION_MISMATCH, "representation:family"),
        (DisagreementCause.REGIME_BOUNDARY, "regime"),
        (DisagreementCause.MODEL_BLIND_SPOT, "model:coverage"),
    ):
        case = _case(cause.value.lower(), dimension)
        route = select_experiment_route(
            cases=(case,),
            diagnoses=(_diagnosis(case, cause),),
            preflight_lineage=lineage,
            stale_report=_fresh(lineage),
        )
        assert route.action is ExperimentRouteAction.RUN_REPLAY
        assert {"leakage", "missingness", "reproducibility"}.issubset(route.required_checks)
