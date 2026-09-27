from __future__ import annotations

import re

from ..contracts import LoopKind
from ..plugins import PluginDecision, PluginDecisionStatus, PluginDescriptor


class PluginSelectionPolicy:
    """Select every materially beneficial, eligible plugin for one top-level run."""

    def select(
        self,
        run_kind: LoopKind,
        objective: str,
        plugins: tuple[PluginDescriptor, ...],
    ) -> tuple[PluginDecision, ...]:
        objective_tokens = set(re.findall(r"[a-z0-9_]+", objective.lower()))
        selected_redundancy_groups: set[str] = set()
        decisions: list[PluginDecision] = []

        for plugin in plugins:
            if not plugin.available:
                decisions.append(self._decision(plugin, PluginDecisionStatus.UNAVAILABLE, "plugin is not available to this run"))
                continue
            if not plugin.policy_eligible:
                decisions.append(self._decision(plugin, PluginDecisionStatus.SKIPPED_POLICY, "plugin is blocked by the current run policy"))
                continue

            deep_required = "deep_research" in plugin.capabilities
            tag_match = bool(objective_tokens.intersection(tag.lower() for tag in plugin.benefit_tags))
            materially_beneficial = deep_required or tag_match

            if not materially_beneficial:
                decisions.append(
                    self._decision(
                        plugin,
                        PluginDecisionStatus.SKIPPED_NOT_BENEFICIAL,
                        f"no marginal benefit tag matched the {run_kind.value} objective",
                    )
                )
                continue

            if plugin.redundancy_group and plugin.redundancy_group in selected_redundancy_groups and not deep_required:
                decisions.append(
                    self._decision(
                        plugin,
                        PluginDecisionStatus.SKIPPED_REDUNDANT,
                        f"redundancy group {plugin.redundancy_group} already has a selected provider",
                    )
                )
                continue

            if plugin.redundancy_group:
                selected_redundancy_groups.add(plugin.redundancy_group)
            reason = "Deep Research is required for top-level research runs" if deep_required else "plugin has positive objective-specific marginal value"
            decisions.append(self._decision(plugin, PluginDecisionStatus.SELECTED, reason))

        return tuple(decisions)

    @staticmethod
    def _decision(
        plugin: PluginDescriptor,
        status: PluginDecisionStatus,
        reason: str,
    ) -> PluginDecision:
        return PluginDecision(
            plugin_id=plugin.plugin_id,
            plugin_descriptor_id=plugin.descriptor_id,
            display_name=plugin.display_name,
            capabilities=plugin.capabilities,
            status=status,
            reason=reason,
        )
