"""Stale-aware research lineage: content-addressed `ResearchLineageManifest`
artifacts and contract-fingerprint `StaleEvidenceReport` detection.

Provenance-manifest ancestry verification lives separately in
`prometheus_loop.provenance_lineage`.
"""

from __future__ import annotations

from collections.abc import Mapping

from .contracts import ResearchLineageManifest, StaleEvidenceReport


def _canonical_contracts(rows: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    seen: dict[str, str] = {}
    for name, fingerprint in rows:
        if not name or not fingerprint:
            raise ValueError("contract fingerprints require non-empty name and fingerprint")
        if name in seen:
            raise ValueError(f"duplicate contract fingerprint for {name}")
        seen[name] = fingerprint
    return tuple(sorted(seen.items()))


def build_lineage_manifest(
    *,
    root_artifact_id: str,
    artifact_ids: tuple[str, ...],
    predecessor_ids: tuple[str, ...],
    contract_fingerprints: tuple[tuple[str, str], ...],
) -> ResearchLineageManifest:
    if not root_artifact_id:
        raise ValueError("lineage root artifact id is required")
    return ResearchLineageManifest(
        root_artifact_id=root_artifact_id,
        artifact_ids=tuple(sorted(set(artifact_ids))),
        predecessor_ids=tuple(sorted(set(predecessor_ids))),
        contract_fingerprints=_canonical_contracts(contract_fingerprints),
    )


def detect_stale_lineage(
    lineage: ResearchLineageManifest,
    current_contract_fingerprints: Mapping[str, str],
) -> StaleEvidenceReport:
    mismatches: list[tuple[str, str, str]] = []
    for name, expected in lineage.contract_fingerprints:
        observed = current_contract_fingerprints.get(name, "<MISSING>")
        if observed != expected:
            mismatches.append((name, expected, observed))
    return StaleEvidenceReport(
        lineage_manifest_id=lineage.artifact_id,
        contract_mismatches=tuple(sorted(mismatches)),
    )
