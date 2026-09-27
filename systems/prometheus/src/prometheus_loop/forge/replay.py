from __future__ import annotations

from collections.abc import Mapping

from ..contracts import (
    AdversarialReport,
    CandidateImprovement,
    CandidateStatus,
    ExperimentSpec,
    RejectedHypothesis,
    ReplayResult,
)


def compare_replay(
    spec: ExperimentSpec,
    baseline_metrics: Mapping[str, float],
    candidate_metrics: Mapping[str, float],
    adversarial_report: AdversarialReport,
) -> CandidateImprovement | RejectedHypothesis:
    baseline = tuple(sorted((str(k), float(v)) for k, v in baseline_metrics.items()))
    candidate = tuple(sorted((str(k), float(v)) for k, v in candidate_metrics.items()))
    replay = ReplayResult(
        experiment_id=spec.artifact_id,
        baseline_metrics=baseline,
        candidate_metrics=candidate,
        deterministic=True,
        passed_guardrails=adversarial_report.passed,
    )

    if not adversarial_report.passed:
        return RejectedHypothesis(
            experiment_id=spec.artifact_id,
            reason=f"Guardrail failure: {', '.join(adversarial_report.failed_checks)}",
            evidence_ids=(adversarial_report.artifact_id, replay.artifact_id),
        )

    baseline_score = float(baseline_metrics.get("score", 0.0))
    candidate_score = float(candidate_metrics.get("score", 0.0))
    baseline_drawdown = baseline_metrics.get("drawdown")
    candidate_drawdown = candidate_metrics.get("drawdown")
    drawdown_ok = (
        baseline_drawdown is None
        or candidate_drawdown is None
        or float(candidate_drawdown) <= float(baseline_drawdown)
    )
    if candidate_score <= baseline_score or not drawdown_ok:
        return RejectedHypothesis(
            experiment_id=spec.artifact_id,
            reason="Candidate did not provide robust incremental improvement over baseline.",
            evidence_ids=(adversarial_report.artifact_id, replay.artifact_id),
        )

    return CandidateImprovement(
        experiment_id=spec.artifact_id,
        status=CandidateStatus.PROMETHEUS_ENGINEERING_PASS,
        evidence_ids=(adversarial_report.artifact_id, replay.artifact_id),
        summary="Candidate improved the controlled replay and survived PROMETHEUS engineering guardrails; DAEDALUS validation is still required.",
    )
