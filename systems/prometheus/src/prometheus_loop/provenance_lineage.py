"""Provenance-ancestry lineage: verify the `parent_manifest_ids` DAG of a
`ResearchProvenanceManifest` against append-only research memory.

This is distinct from `prometheus_loop.lineage`, which builds stale-aware
research lineage manifests and contract-fingerprint staleness reports.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ids import content_id
from .memory.store import ResearchMemory


@dataclass(frozen=True)
class ProvenanceLineageReport:
    tip_manifest_id: str
    verified_manifest_ids: tuple[str, ...]
    root_manifest_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    complete: bool
    failure_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.tip_manifest_id.startswith("research-provenance:"):
            raise ValueError("lineage tip must use research-provenance: namespace")
        for name in ("verified_manifest_ids", "root_manifest_ids", "edge_ids", "failure_reasons"):
            values = getattr(self, name)
            if len(set(values)) != len(values):
                raise ValueError(f"duplicate identifier in {name}")
            object.__setattr__(self, name, tuple(sorted(values)))
        if self.complete and self.failure_reasons:
            raise ValueError("complete provenance lineage cannot contain failure reasons")

    @property
    def artifact_id(self) -> str:
        return content_id("provenance-lineage", self)


def verify_provenance_lineage(memory: ResearchMemory, tip_manifest_id: str) -> ProvenanceLineageReport:
    verified: set[str] = set()
    roots: set[str] = set()
    edges: set[str] = set()
    failures: set[str] = set()
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(manifest_id: str) -> None:
        if manifest_id in visiting:
            failures.add(f"provenance cycle detected at {manifest_id}")
            return
        if manifest_id in visited:
            return
        try:
            record = memory.find_by_id(manifest_id)
        except KeyError:
            failures.add(f"missing parent manifest {manifest_id}")
            return
        if record.get("artifact_type") != "ResearchProvenanceManifest":
            failures.add(f"wrong artifact type for provenance manifest {manifest_id}")
            visited.add(manifest_id)
            return

        payload = record.get("payload", {})
        parents = tuple(payload.get("parent_manifest_ids", ()))
        if len(set(parents)) != len(parents):
            failures.add(f"duplicate parent manifest identifier in {manifest_id}")

        visiting.add(manifest_id)
        for parent_id in sorted(set(parents)):
            edges.add(f"{parent_id} -> {manifest_id}")
            visit(parent_id)
        visiting.remove(manifest_id)

        try:
            memory.reconstruct_provenance_manifest(manifest_id)
        except (KeyError, TypeError, ValueError) as exc:
            failures.add(str(exc))
        else:
            verified.add(manifest_id)
            if not parents:
                roots.add(manifest_id)
        visited.add(manifest_id)

    visit(tip_manifest_id)
    return ProvenanceLineageReport(
        tip_manifest_id=tip_manifest_id,
        verified_manifest_ids=tuple(verified),
        root_manifest_ids=tuple(roots),
        edge_ids=tuple(edges),
        complete=not failures and tip_manifest_id in verified,
        failure_reasons=tuple(failures),
    )
