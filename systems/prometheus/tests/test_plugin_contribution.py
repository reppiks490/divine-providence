from prometheus_loop.contracts import PluginContributionOutcome
from prometheus_loop.forge.plugin_contribution import evaluate_plugin_contributions
from prometheus_loop.plugins import PluginDecisionStatus, PluginExecutionEvidence


def _evidence(plugin_id, *, status=PluginDecisionStatus.COMPLETED, contributions=()):
    return PluginExecutionEvidence(
        loop_run_id="loop:test",
        plugin_id=plugin_id,
        plugin_descriptor_id=f"plugin:{plugin_id}",
        status=status,
        input_fingerprint=f"input:{plugin_id}",
        output_fingerprint=(f"output:{plugin_id}" if status is PluginDecisionStatus.COMPLETED else None),
        failure_class=("timeout" if status is PluginDecisionStatus.FAILED else None),
        contributed_artifact_ids=tuple(contributions),
    )


def test_contribution_reports_classify_unique_shared_zero_and_failed_deterministically():
    evidence = (
        _evidence("exa", contributions=("artifact:shared", "artifact:exa-only")),
        _evidence("deep-research", contributions=("artifact:shared", "artifact:dr-only")),
        _evidence("tavily"),
        _evidence("firecrawl", status=PluginDecisionStatus.FAILED),
    )

    reports = evaluate_plugin_contributions(tuple(reversed(evidence)))
    by_id = {report.plugin_id: report for report in reports}

    assert tuple(report.plugin_id for report in reports) == (
        "deep-research",
        "exa",
        "firecrawl",
        "tavily",
    )
    assert by_id["deep-research"].outcome is PluginContributionOutcome.UNIQUE_AND_SHARED
    assert by_id["deep-research"].unique_artifact_ids == ("artifact:dr-only",)
    assert by_id["deep-research"].shared_artifact_ids == ("artifact:shared",)
    assert by_id["exa"].outcome is PluginContributionOutcome.UNIQUE_AND_SHARED
    assert by_id["exa"].unique_artifact_ids == ("artifact:exa-only",)
    assert by_id["tavily"].outcome is PluginContributionOutcome.NO_ATTRIBUTED_ARTIFACTS
    assert by_id["firecrawl"].outcome is PluginContributionOutcome.FAILED
    assert by_id["firecrawl"].failure_class == "timeout"


def test_duplicate_ids_within_one_plugin_do_not_create_false_shared_contribution():
    reports = evaluate_plugin_contributions(
        (_evidence("exa", contributions=("artifact:one", "artifact:one")),)
    )
    report = reports[0]
    assert report.outcome is PluginContributionOutcome.UNIQUE
    assert report.unique_artifact_ids == ("artifact:one",)
    assert report.shared_artifact_ids == ()
