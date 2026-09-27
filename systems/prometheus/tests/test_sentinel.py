import pytest

from prometheus_loop.contracts import ObservationEnvelope
from prometheus_loop.sentinel.disagreement import detect_disagreements
from prometheus_loop.sentinel.validate import validate_same_instant


def obs(sibling, instant="2026-09-24T15:00:00Z", availability="KNOWN", **dims):
    return ObservationEnvelope(
        sibling=sibling,
        decision_instant=instant,
        availability_state=availability,
        evidence_tier="TEST",
        dimensions=tuple(sorted((key, str(value)) for key, value in dims.items())),
        source_ref=f"{sibling.lower()}:fixture",
    )


def test_mismatched_decision_instants_fail_closed():
    observations = (
        obs("NEXUS", direction="bullish"),
        obs("ATHENA", instant="2026-09-24T15:01:00Z", direction="bullish"),
    )
    with pytest.raises(ValueError, match="decision instant"):
        validate_same_instant(observations)


def test_unknown_availability_fails_closed():
    observations = (
        obs("NEXUS", availability="UNKNOWN", direction="bullish"),
        obs("ATHENA", direction="bullish"),
    )
    with pytest.raises(ValueError, match="availability"):
        validate_same_instant(observations)


def test_identical_claims_produce_no_disagreement():
    observations = (
        obs("NEXUS", direction="bullish", confidence="0.70"),
        obs("ATHENA", direction="bullish", confidence="0.70"),
    )
    assert detect_disagreements(observations) == ()


def test_direction_and_confidence_disagreements_are_typed_and_deterministic():
    observations = (
        obs("NEXUS", direction="bullish", confidence="0.81"),
        obs("ATHENA", direction="bearish", confidence="0.45"),
        obs("ARGUS", direction="bullish", confidence="0.61"),
    )
    first = detect_disagreements(observations)
    second = detect_disagreements(tuple(reversed(observations)))
    assert [case.disagreement_type for case in first] == ["CONFIDENCE", "DIRECTIONAL"]
    assert [case.artifact_id for case in first] == [case.artifact_id for case in second]
