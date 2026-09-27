"""Topology-aware safety constraints for Infrastructure Supervisory Loop V4.

This module can only *reduce* mutation authority. It never proposes actions.
Topology is operator-supplied and immutable for a governor instance.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

HIGH_IMPACT = frozenset({'restart', 'scale', 'repair', 'isolate'})


@dataclass(frozen=True)
class ComponentTopology:
    name: str
    depends_on: Tuple[str, ...] = ()
    failure_domain: Optional[str] = None
    redundancy_group: Optional[str] = None
    min_healthy: int = 1
    critical: bool = False
    authority: str = 'local'


@dataclass(frozen=True)
class TopologyDecision:
    approved: bool
    reason: str
    impacted_components: Tuple[str, ...] = ()
    lease_scopes: Tuple[str, ...] = ()


class TopologyModel:
    def __init__(self, components: Sequence[ComponentTopology]):
        self.components = {c.name: c for c in components}
        self._dependents = {name: set() for name in self.components}
        for c in components:
            for dependency in c.depends_on:
                if dependency in self._dependents:
                    self._dependents[dependency].add(c.name)

    def get(self, name: str) -> Optional[ComponentTopology]:
        return self.components.get(name)

    def impacted(self, name: str) -> Tuple[str, ...]:
        if name not in self.components:
            return ()
        seen = {name}
        todo = [name]
        while todo:
            current = todo.pop()
            for downstream in self._dependents.get(current, ()):
                if downstream not in seen:
                    seen.add(downstream)
                    todo.append(downstream)
        return tuple(sorted(seen))

    def group_members(self, group: str) -> Tuple[ComponentTopology, ...]:
        return tuple(c for c in self.components.values() if c.redundancy_group == group)


class BlastRadiusGovernor:
    """Pure authorization constraint over an already-proposed action."""
    def __init__(self, model: TopologyModel, healthy_threshold: float = 0.50):
        self.model = model
        self.healthy_threshold = healthy_threshold

    @staticmethod
    def _class_value(action) -> str:
        value = getattr(action.action_class, 'value', action.action_class)
        return str(value)

    def evaluate(self, action, health_scores: Optional[Mapping[str, float]] = None) -> TopologyDecision:
        high_impact = self._class_value(action) in HIGH_IMPACT
        node = self.model.get(action.component)
        if node is None:
            if high_impact:
                return TopologyDecision(False, 'unknown topology for high-impact mutation')
            return TopologyDecision(True, 'low-impact action allowed with unknown topology')

        impacted = self.model.impacted(node.name)
        scopes = [f'component:{node.name}']
        if node.failure_domain:
            scopes.append(f'failure-domain:{node.failure_domain}')
        if node.redundancy_group:
            scopes.append(f'redundancy-group:{node.redundancy_group}')

        if node.authority != 'local':
            return TopologyDecision(
                False, f'component authority is external: {node.authority}', impacted, tuple(scopes)
            )

        if high_impact:
            critical_downstream = [
                name for name in impacted if name != node.name and self.model.components[name].critical
            ]
            if critical_downstream:
                return TopologyDecision(
                    False,
                    'critical downstream dependency would enter blast radius',
                    impacted,
                    tuple(scopes),
                )

            if node.redundancy_group:
                if health_scores is None:
                    return TopologyDecision(
                        False, 'health context required for redundancy budget', impacted, tuple(scopes)
                    )
                members = self.model.group_members(node.redundancy_group)
                healthy_after = sum(
                    1 for member in members
                    if member.name != node.name and health_scores.get(member.name, 0.0) >= self.healthy_threshold
                )
                minimum = max(member.min_healthy for member in members)
                if healthy_after < minimum:
                    return TopologyDecision(
                        False,
                        'redundancy budget would fall below minimum healthy members',
                        impacted,
                        tuple(scopes),
                    )

        return TopologyDecision(True, 'topology constraints satisfied', impacted, tuple(scopes))


@dataclass(frozen=True)
class _Lease:
    owner: str
    expires_at: float


class MutationLeaseManager:
    """Process-local lease manager. Not a distributed lock."""
    def __init__(self):
        self._leases: dict[str, _Lease] = {}

    def _prune(self, now: float) -> None:
        for scope in list(self._leases):
            if self._leases[scope].expires_at <= now:
                del self._leases[scope]

    def acquire(self, owner: str, scopes: Sequence[str], ttl_seconds: float, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        self._prune(now)
        unique = tuple(dict.fromkeys(scopes))
        if any(scope in self._leases and self._leases[scope].owner != owner for scope in unique):
            return False
        expiry = now + max(0.001, ttl_seconds)
        for scope in unique:
            self._leases[scope] = _Lease(owner, expiry)
        return True

    def release(self, owner: str) -> None:
        for scope in list(self._leases):
            if self._leases[scope].owner == owner:
                del self._leases[scope]
