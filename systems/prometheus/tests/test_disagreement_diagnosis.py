from prometheus_loop.contracts import (
    DisagreementCase,
    DisagreementCause,
    ObservationEnvelope,
)
from prometheus_loop.sentinel.diagnosis import diagnose_disagreement


def _obs(name: str, *, availability: str = "KNOWN", tier: str = "TIER", dims=()):
    return ObservationEnvelope(
        sibling=name,
        decision_instant="160",
        availability_state=availability,
        evidence_tier=tier,
        dimensions=tuple(dims),
        source_ref=f"src:{name}",
    )


def _case(dimension: str, observations):
    return DisagreementCase(
        decision_instant="160",
        dimension=dimension,
        observation_ids=tuple(item.artifact_id for item in observations),
        values=("a", "b"),
        disagreement_type="VALUE",
    )


def test_role_specific_contract_difference_is_intentional_specialization():
    observations = (_obs("ARGUS"), _obs("ATHENA"))
    diagnosis = diagnose_disagreement(_case("contract", observations), observations)
    assert diagnosis.cause is DisagreementCause.INTENTIONAL_SPECIALIZATION


def test_availability_mismatch_has_highest_precedence():
    observations = (
        _obs("ARGUS", availability="KNOWN"),
        _obs("ATHENA", availability="UNKNOWN"),
    )
    diagnosis = diagnose_disagreement(_case("contract", observations), observations)
    assert diagnosis.cause is DisagreementCause.AVAILABILITY_MISMATCH


def test_source_health_dimension_classifies_source_health_issue():
    observations = (_obs("NEXUS"), _obs("ATHENA"))
    diagnosis = diagnose_disagreement(_case("source_health:healthy_fraction", observations), observations)
    assert diagnosis.cause is DisagreementCause.SOURCE_HEALTH_ISSUE


def test_representation_dimension_classifies_representation_mismatch():
    observations = (_obs("NEXUS"), _obs("ARGUS"))
    diagnosis = diagnose_disagreement(_case("representation:family", observations), observations)
    assert diagnosis.cause is DisagreementCause.REPRESENTATION_MISMATCH


def test_regime_dimension_classifies_regime_boundary():
    observations = (_obs("ATHENA"), _obs("NEXUS"))
    diagnosis = diagnose_disagreement(_case("regime", observations), observations)
    assert diagnosis.cause is DisagreementCause.REGIME_BOUNDARY


def test_shared_context_difference_classifies_evidence_mismatch():
    observations = (_obs("NEXUS"), _obs("DAEDALUS"))
    diagnosis = diagnose_disagreement(_case("factor:tech", observations), observations)
    assert diagnosis.cause is DisagreementCause.EVIDENCE_MISMATCH


def test_unknown_dimension_stays_irreducibly_ambiguous():
    observations = (_obs("X"), _obs("Y"))
    diagnosis = diagnose_disagreement(_case("future:new_dimension", observations), observations)
    assert diagnosis.cause is DisagreementCause.IRREDUCIBLE_AMBIGUITY


def test_diagnosis_rejects_case_with_missing_observation():
    observations = (_obs("NEXUS"), _obs("ARGUS"))
    case = DisagreementCase(
        decision_instant="160",
        dimension="factor:tech",
        observation_ids=(observations[0].artifact_id, "observation:missing"),
        values=("a", "b"),
        disagreement_type="VALUE",
    )
    try:
        diagnose_disagreement(case, observations)
    except ValueError as exc:
        assert "missing observation" in str(exc)
    else:
        raise AssertionError("expected missing observation to fail closed")
