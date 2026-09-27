from __future__ import annotations

from collections import Counter

from ..contracts import PluginContributionOutcome, PluginContributionReport
from ..plugins import PluginDecisionStatus, PluginExecutionEvidence


def evaluate_plugin_contributions(
    evidence: tuple[PluginExecutionEvidence, ...],
) -> tuple[PluginContributionReport, ...]:
    counts = Counter(
        artifact_id
        for item in evidence
        if item.status is PluginDecisionStatus.COMPLETED
        for artifact_id in set(item.contributed_artifact_ids)
    )
    reports: list[PluginContributionReport] = []
    for item in sorted(evidence, key=lambda row: row.plugin_id):
        if item.status is PluginDecisionStatus.FAILED:
            outcome = PluginContributionOutcome.FAILED
            unique_ids: tuple[str, ...] = ()
            shared_ids: tuple[str, ...] = ()
        else:
            attributed = set(item.contributed_artifact_ids)
            unique_ids = tuple(sorted(a for a in attributed if counts[a] == 1))
            shared_ids = tuple(sorted(a for a in attributed if counts[a] > 1))
            if unique_ids and shared_ids:
                outcome = PluginContributionOutcome.UNIQUE_AND_SHARED
            elif unique_ids:
                outcome = PluginContributionOutcome.UNIQUE
            elif shared_ids:
                outcome = PluginContributionOutcome.SHARED
            else:
                outcome = PluginContributionOutcome.NO_ATTRIBUTED_ARTIFACTS
        reports.append(
            PluginContributionReport(
                loop_run_id=item.loop_run_id,
                plugin_id=item.plugin_id,
                plugin_evidence_id=item.artifact_id,
                outcome=outcome,
                unique_artifact_ids=unique_ids,
                shared_artifact_ids=shared_ids,
                failure_class=item.failure_class,
            )
        )
    return tuple(reports)
