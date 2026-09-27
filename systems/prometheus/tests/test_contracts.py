from dataclasses import FrozenInstanceError

import pytest

from prometheus_loop.contracts import (
    CandidateImprovement,
    CandidateStatus,
    DisagreementCase,
    ExperimentSpec,
    LoopKind,
    ObservationEnvelope,
    RejectedHypothesis,
    ReplayResult,
    ResearchHypothesis,
    RunStatus,
)
from prometheus_loop.ids import canonical_json, content_id


def test_canonical_json_and_content_id_are_key_order_independent():
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}
    assert canonical_json(left) == canonical_json(right)
    assert content_id("x", left) == content_id("x", right)


def test_observation_id_is_deterministic_and_artifact_is_frozen():
    observation = ObservationEnvelope(
        sibling="ATHENA",
        decision_instant="2026-09-24T15:00:00Z",
        availability_state="KNOWN",
        evidence_tier="SUPERVISORY",
        dimensions=(("direction", "bullish"), ("confidence", "0.72")),
        source_ref="athena:test:1",
    )
    same = ObservationEnvelope(
        sibling="ATHENA",
        decision_instant="2026-09-24T15:00:00Z",
        availability_state="KNOWN",
        evidence_tier="SUPERVISORY",
        dimensions=(("direction", "bullish"), ("confidence", "0.72")),
        source_ref="athena:test:1",
    )
    assert observation.artifact_id == same.artifact_id
    with pytest.raises(FrozenInstanceError):
        observation.sibling = "ARGUS"


def test_candidate_status_has_no_production_authorized_state():
    assert {item.value for item in CandidateStatus} == {
        "RESEARCH_ONLY",
        "PROMETHEUS_ENGINEERING_PASS",
    }
    assert "production_authorized" not in CandidateImprovement.__dataclass_fields__


def test_core_artifacts_can_be_constructed_without_production_authority():
    disagreement = DisagreementCase(
        decision_instant="2026-09-24T15:00:00Z",
        dimension="direction",
        observation_ids=("obs:a", "obs:b"),
        values=("bullish", "bearish"),
        disagreement_type="DIRECTIONAL",
    )
    hypothesis = ResearchHypothesis(
        case_id=disagreement.artifact_id,
        family="EVIDENCE_MISMATCH",
        claim="Observed disagreement is caused by evidence mismatch.",
        falsifier="Same eligible evidence still produces the disagreement.",
    )
    spec = ExperimentSpec(
        hypothesis_id=hypothesis.artifact_id,
        decision_instant=disagreement.decision_instant,
        checks=("leakage", "reproducibility"),
    )
    replay = ReplayResult(
        experiment_id=spec.artifact_id,
        baseline_metrics=(("score", 0.5),),
        candidate_metrics=(("score", 0.6),),
        deterministic=True,
        passed_guardrails=True,
    )
    candidate = CandidateImprovement(
        experiment_id=spec.artifact_id,
        status=CandidateStatus.PROMETHEUS_ENGINEERING_PASS,
        evidence_ids=(replay.artifact_id,),
        summary="Candidate survived engineering checks only.",
    )
    rejected = RejectedHypothesis(
        experiment_id=spec.artifact_id,
        reason="Synthetic rejection fixture.",
        evidence_ids=(replay.artifact_id,),
    )
    assert LoopKind.FORGE.value == "FORGE"
    assert RunStatus.RESEARCH_COMPLETE.value == "RESEARCH_COMPLETE"
    assert candidate.status is CandidateStatus.PROMETHEUS_ENGINEERING_PASS
    assert rejected.artifact_id.startswith("rejected:")
