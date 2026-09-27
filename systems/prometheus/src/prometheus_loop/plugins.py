from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .contracts import RunStatus
from .ids import content_id


class PluginDecisionStatus(str, Enum):
    SELECTED = "SELECTED"
    SKIPPED_NOT_BENEFICIAL = "SKIPPED_NOT_BENEFICIAL"
    SKIPPED_REDUNDANT = "SKIPPED_REDUNDANT"
    SKIPPED_POLICY = "SKIPPED_POLICY"
    UNAVAILABLE = "UNAVAILABLE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PluginDescriptor:
    plugin_id: str
    display_name: str
    capabilities: tuple[str, ...]
    benefit_tags: tuple[str, ...]
    available: bool = True
    policy_eligible: bool = True
    redundancy_group: str | None = None

    @property
    def descriptor_id(self) -> str:
        return content_id("plugin", self)


@dataclass(frozen=True)
class PluginDecision:
    plugin_id: str
    plugin_descriptor_id: str
    display_name: str
    capabilities: tuple[str, ...]
    status: PluginDecisionStatus
    reason: str


@dataclass(frozen=True)
class PluginUseRecord:
    loop_run_id: str
    plugin_id: str
    status: PluginDecisionStatus
    input_fingerprint: str
    output_fingerprint: str | None = None
    external_result_ref: str | None = None
    failure_class: str | None = None
    contributed_artifact_ids: tuple[str, ...] = ()

    @classmethod
    def completed(
        cls,
        *,
        loop_run_id: str,
        plugin_id: str,
        input_fingerprint: str,
        output_fingerprint: str | None = None,
        external_result_ref: str | None = None,
        contributed_artifact_ids: tuple[str, ...] = (),
    ) -> "PluginUseRecord":
        if not output_fingerprint and not external_result_ref:
            raise ValueError("completed plugin use requires output fingerprint or external result reference")
        return cls(
            loop_run_id=loop_run_id,
            plugin_id=plugin_id,
            status=PluginDecisionStatus.COMPLETED,
            input_fingerprint=input_fingerprint,
            output_fingerprint=output_fingerprint,
            external_result_ref=external_result_ref,
            contributed_artifact_ids=contributed_artifact_ids,
        )

    @classmethod
    def failed(
        cls,
        *,
        loop_run_id: str,
        plugin_id: str,
        input_fingerprint: str,
        failure_class: str,
    ) -> "PluginUseRecord":
        if not failure_class:
            raise ValueError("failed plugin use requires failure_class")
        return cls(
            loop_run_id=loop_run_id,
            plugin_id=plugin_id,
            status=PluginDecisionStatus.FAILED,
            input_fingerprint=input_fingerprint,
            failure_class=failure_class,
        )




@dataclass(frozen=True)
class PluginExecutionEvidence:
    loop_run_id: str
    plugin_id: str
    plugin_descriptor_id: str
    status: PluginDecisionStatus
    input_fingerprint: str
    output_fingerprint: str | None = None
    external_result_ref: str | None = None
    failure_class: str | None = None
    contributed_artifact_ids: tuple[str, ...] = ()

    @property
    def artifact_id(self) -> str:
        return content_id("plugin-evidence", self)


def normalize_plugin_evidence(
    audit: "PluginAudit",
    inventory: tuple[PluginDescriptor, ...],
) -> tuple[PluginExecutionEvidence, ...]:
    descriptors = {item.plugin_id: item for item in inventory}
    evidence: list[PluginExecutionEvidence] = []
    for decision in audit.decisions:
        if decision.status is not PluginDecisionStatus.SELECTED:
            continue
        descriptor = descriptors.get(decision.plugin_id)
        if descriptor is None:
            raise ValueError(f"plugin descriptor missing for selected plugin {decision.plugin_id}")
        if descriptor.descriptor_id != decision.plugin_descriptor_id:
            raise ValueError(f"plugin descriptor drift for selected plugin {decision.plugin_id}")
        use = audit.use_for(decision.plugin_id)
        evidence.append(
            PluginExecutionEvidence(
                loop_run_id=audit.loop_run_id,
                plugin_id=use.plugin_id,
                plugin_descriptor_id=descriptor.descriptor_id,
                status=use.status,
                input_fingerprint=use.input_fingerprint,
                output_fingerprint=use.output_fingerprint,
                external_result_ref=use.external_result_ref,
                failure_class=use.failure_class,
                contributed_artifact_ids=tuple(sorted(use.contributed_artifact_ids)),
            )
        )
    return tuple(sorted(evidence, key=lambda item: item.plugin_id))


@dataclass(frozen=True)
class PluginAudit:
    loop_run_id: str
    decisions: tuple[PluginDecision, ...]
    uses: tuple[PluginUseRecord, ...] = ()

    @property
    def artifact_id(self) -> str:
        return content_id("plugin-audit", self)

    def record_use(self, use: PluginUseRecord) -> "PluginAudit":
        if use.loop_run_id != self.loop_run_id:
            raise ValueError("plugin use belongs to a different loop run")
        selected = {d.plugin_id for d in self.decisions if d.status is PluginDecisionStatus.SELECTED}
        if use.plugin_id not in selected:
            raise ValueError(f"plugin {use.plugin_id} was not selected")
        remaining = tuple(item for item in self.uses if item.plugin_id != use.plugin_id)
        return replace(self, uses=remaining + (use,))

    def use_for(self, plugin_id: str) -> PluginUseRecord:
        for use in self.uses:
            if use.plugin_id == plugin_id:
                return use
        raise KeyError(plugin_id)

    def _deep_research_decision(self) -> PluginDecision | None:
        for decision in self.decisions:
            if "deep_research" in decision.capabilities:
                return decision
        return None

    def finalize(self, requested_status: RunStatus) -> RunStatus:
        deep = self._deep_research_decision()
        if requested_status is RunStatus.RESEARCH_COMPLETE and deep is not None:
            if deep.status is PluginDecisionStatus.SELECTED:
                try:
                    use = self.use_for(deep.plugin_id)
                except KeyError as exc:
                    raise ValueError("Deep Research was selected but not completed") from exc
                if use.status is not PluginDecisionStatus.COMPLETED:
                    raise ValueError("Deep Research did not complete successfully")
            elif deep.status is PluginDecisionStatus.UNAVAILABLE:
                raise ValueError("Deep Research is unavailable; use DEGRADED_RESEARCH")
        return requested_status
