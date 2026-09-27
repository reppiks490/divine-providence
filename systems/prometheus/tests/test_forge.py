from prometheus_loop.contracts import (
    CandidateImprovement,
    CandidateStatus,
    DisagreementCase,
    ExperimentSpec,
    RejectedHypothesis,
)
from prometheus_loop.forge.adversarial import run_adversarial
from prometheus_loop.forge.hypothesis import hypothesis_from_case
from prometheus_loop.forge.replay import compare_replay


def case():
    return DisagreementCase(
        decision_instant="2026-09-24T15:00:00Z",
        dimension="direction",
        observation_ids=("observation:a", "observation:b"),
        values=("bullish", "bearish"),
        disagreement_type="DIRECTIONAL",
    )


def spec():
    hypothesis = hypothesis_from_case(case())
    return ExperimentSpec(
        hypothesis_id=hypothesis.artifact_id,
        decision_instant=case().decision_instant,
        checks=("leakage", "ablation", "perturbation", "missingness", "reproducibility"),
    )


def clean_candidate(**overrides):
    candidate = {
        "uses_future": False,
        "ablation_stable": True,
        "perturbation_stable": True,
        "missingness_safe": True,
        "replay_hashes": ("same", "same"),
    }
    candidate.update(overrides)
    return candidate


def test_hypothesis_from_same_case_is_deterministic_and_falsifiable():
    first = hypothesis_from_case(case())
    second = hypothesis_from_case(case())
    assert first.artifact_id == second.artifact_id
    assert first.claim
    assert first.falsifier


def test_leaky_candidate_is_rejected_by_adversarial_suite():
    report = run_adversarial(spec(), baseline={}, candidate=clean_candidate(uses_future=True))
    assert report.passed is False
    assert "leakage" in report.failed_checks


def test_reproducibility_mismatch_is_rejected():
    report = run_adversarial(
        spec(),
        baseline={},
        candidate=clean_candidate(replay_hashes=("hash-a", "hash-b")),
    )
    assert report.passed is False
    assert "reproducibility" in report.failed_checks


def test_clean_candidate_can_only_reach_engineering_pass():
    experiment = spec()
    report = run_adversarial(experiment, baseline={}, candidate=clean_candidate())
    result = compare_replay(
        experiment,
        baseline_metrics={"score": 0.50, "drawdown": 0.20},
        candidate_metrics={"score": 0.61, "drawdown": 0.18},
        adversarial_report=report,
    )
    assert isinstance(result, CandidateImprovement)
    assert result.status is CandidateStatus.PROMETHEUS_ENGINEERING_PASS
    assert "production_authorized" not in result.__dataclass_fields__


def test_guardrail_failure_overrides_metric_improvement():
    experiment = spec()
    report = run_adversarial(experiment, baseline={}, candidate=clean_candidate(missingness_safe=False))
    result = compare_replay(
        experiment,
        baseline_metrics={"score": 0.50},
        candidate_metrics={"score": 0.90},
        adversarial_report=report,
    )
    assert isinstance(result, RejectedHypothesis)
    assert "guardrail" in result.reason.lower()
