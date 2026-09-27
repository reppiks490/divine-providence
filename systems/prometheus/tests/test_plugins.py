import pytest

from prometheus_loop.contracts import LoopKind, RunStatus
from prometheus_loop.plugins import (
    PluginAudit,
    PluginDecisionStatus,
    PluginDescriptor,
    PluginUseRecord,
)
from prometheus_loop.policy.plugins import PluginSelectionPolicy


def inventory():
    return (
        PluginDescriptor(
            plugin_id="deep-research",
            display_name="Deep Research",
            capabilities=("deep_research", "web_research"),
            benefit_tags=("research", "architecture", "validation"),
        ),
        PluginDescriptor(
            plugin_id="exa",
            display_name="Exa",
            capabilities=("web_research",),
            benefit_tags=("research", "sources", "architecture"),
        ),
        PluginDescriptor(
            plugin_id="gmail",
            display_name="Gmail",
            capabilities=("email",),
            benefit_tags=("email", "inbox"),
        ),
    )


def test_policy_selects_deep_research_and_all_materially_beneficial_plugins():
    decisions = PluginSelectionPolicy().select(
        LoopKind.FORGE,
        "research architecture validation and source-backed plugin orchestration",
        inventory(),
    )
    by_id = {decision.plugin_id: decision for decision in decisions}
    assert by_id["deep-research"].status is PluginDecisionStatus.SELECTED
    assert by_id["exa"].status is PluginDecisionStatus.SELECTED
    assert by_id["gmail"].status is PluginDecisionStatus.SKIPPED_NOT_BENEFICIAL
    assert by_id["gmail"].reason


def test_policy_records_unavailable_and_policy_blocked_plugins_explicitly():
    plugins = (
        PluginDescriptor(
            plugin_id="offline",
            display_name="Offline Research",
            capabilities=("research",),
            benefit_tags=("research",),
            available=False,
        ),
        PluginDescriptor(
            plugin_id="write-tool",
            display_name="Write Tool",
            capabilities=("repo_write",),
            benefit_tags=("architecture",),
            policy_eligible=False,
        ),
    )
    decisions = PluginSelectionPolicy().select(LoopKind.ASCENSION, "architecture research", plugins)
    assert decisions[0].status is PluginDecisionStatus.UNAVAILABLE
    assert decisions[1].status is PluginDecisionStatus.SKIPPED_POLICY
    assert all(decision.reason for decision in decisions)


def test_audit_requires_deep_research_completion_when_available_and_selected():
    decisions = PluginSelectionPolicy().select(
        LoopKind.FORGE,
        "research architecture validation",
        inventory(),
    )
    audit = PluginAudit(loop_run_id="loop:test", decisions=decisions)
    with pytest.raises(ValueError, match="Deep Research"):
        audit.finalize(RunStatus.RESEARCH_COMPLETE)

    audit = audit.record_use(
        PluginUseRecord.completed(
            loop_run_id="loop:test",
            plugin_id="deep-research",
            input_fingerprint="in:1",
            output_fingerprint="out:1",
            contributed_artifact_ids=("hypothesis:1",),
        )
    )
    assert audit.finalize(RunStatus.RESEARCH_COMPLETE) is RunStatus.RESEARCH_COMPLETE


def test_audit_allows_degraded_research_when_deep_research_is_unavailable():
    plugins = (
        PluginDescriptor(
            plugin_id="deep-research",
            display_name="Deep Research",
            capabilities=("deep_research",),
            benefit_tags=("research",),
            available=False,
        ),
    )
    decisions = PluginSelectionPolicy().select(LoopKind.FORGE, "research", plugins)
    audit = PluginAudit(loop_run_id="loop:test", decisions=decisions)
    assert audit.finalize(RunStatus.DEGRADED_RESEARCH) is RunStatus.DEGRADED_RESEARCH


def test_failed_selected_plugin_is_retained_in_audit():
    decisions = PluginSelectionPolicy().select(
        LoopKind.FORGE,
        "research architecture validation",
        inventory(),
    )
    audit = PluginAudit(loop_run_id="loop:test", decisions=decisions)
    failed = PluginUseRecord.failed(
        loop_run_id="loop:test",
        plugin_id="exa",
        input_fingerprint="in:2",
        failure_class="timeout",
    )
    audit = audit.record_use(failed)
    assert audit.use_for("exa").status is PluginDecisionStatus.FAILED
    assert audit.use_for("exa").failure_class == "timeout"
