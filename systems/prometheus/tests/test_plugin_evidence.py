import pytest

from prometheus_loop.contracts import LoopKind
from prometheus_loop.plugins import (
    PluginAudit,
    PluginDecisionStatus,
    PluginDescriptor,
    PluginUseRecord,
    normalize_plugin_evidence,
)
from prometheus_loop.policy.plugins import PluginSelectionPolicy


def _inventory():
    return (
        PluginDescriptor(
            plugin_id="deep-research",
            display_name="Deep Research",
            capabilities=("deep_research", "web_research"),
            benefit_tags=("research", "architecture"),
        ),
        PluginDescriptor(
            plugin_id="exa",
            display_name="Exa",
            capabilities=("web_research",),
            benefit_tags=("research", "sources"),
        ),
    )


def _audit():
    decisions = PluginSelectionPolicy().select(
        LoopKind.FORGE,
        "research architecture with sources",
        _inventory(),
    )
    audit = PluginAudit(loop_run_id="loop:test", decisions=decisions)
    audit = audit.record_use(
        PluginUseRecord.completed(
            loop_run_id="loop:test",
            plugin_id="deep-research",
            input_fingerprint="input:dr",
            external_result_ref="deep:report:1",
            contributed_artifact_ids=("artifact:alpha",),
        )
    )
    audit = audit.record_use(
        PluginUseRecord.failed(
            loop_run_id="loop:test",
            plugin_id="exa",
            input_fingerprint="input:exa",
            failure_class="timeout",
        )
    )
    return audit


def test_normalized_plugin_evidence_binds_descriptor_and_preserves_execution_fields():
    inventory = _inventory()
    evidence = normalize_plugin_evidence(_audit(), inventory)
    by_id = {item.plugin_id: item for item in evidence}

    assert tuple(item.plugin_id for item in evidence) == ("deep-research", "exa")
    assert by_id["deep-research"].plugin_descriptor_id == inventory[0].descriptor_id
    assert by_id["deep-research"].status is PluginDecisionStatus.COMPLETED
    assert by_id["deep-research"].external_result_ref == "deep:report:1"
    assert by_id["deep-research"].contributed_artifact_ids == ("artifact:alpha",)
    assert by_id["exa"].plugin_descriptor_id == inventory[1].descriptor_id
    assert by_id["exa"].status is PluginDecisionStatus.FAILED
    assert by_id["exa"].failure_class == "timeout"
    assert by_id["deep-research"].artifact_id == normalize_plugin_evidence(_audit(), inventory)[0].artifact_id


def test_normalized_plugin_evidence_rejects_inventory_identity_mismatch():
    wrong_inventory = (
        PluginDescriptor(
            plugin_id="deep-research-v2",
            display_name="Deep Research",
            capabilities=("deep_research",),
            benefit_tags=("research",),
        ),
    )
    with pytest.raises(ValueError, match="descriptor"):
        normalize_plugin_evidence(_audit(), wrong_inventory)

def test_normalized_plugin_evidence_rejects_same_id_descriptor_drift():
    inventory = _inventory()
    audit = _audit()
    drifted_inventory = (
        PluginDescriptor(
            plugin_id="deep-research",
            display_name="Deep Research v2",
            capabilities=("deep_research", "web_research", "new_capability"),
            benefit_tags=("research", "architecture"),
        ),
        inventory[1],
    )
    with pytest.raises(ValueError, match="descriptor drift"):
        normalize_plugin_evidence(audit, drifted_inventory)

