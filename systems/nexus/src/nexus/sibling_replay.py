from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from .adapters import (
    aion_bar_observation,
    aion_source_spec,
    aion_derivation_source_spec,
    aion_derivation_observation,
    aion_source_health_spec,
    aion_source_health_observation,
    argus_candle_proxy_feature,
    athena_provenance,
    daedalus_candidate,
    for_argus,
    for_athena,
    market_state_packet,
)
from .contracts import ReplayBatch, ReplayInstant, StatePacket, StreamManifest
from .lineage import DerivationRecord
from .source_health import SourceHealthPlane


@dataclass(frozen=True, slots=True)
class SiblingInstantBundle:
    """One causally atomic NEXUS market instant routed to sibling-safe payloads."""

    decision_ns: int
    frame_hash: str
    bundle_hash: str
    aion: dict[str, Any]
    argus: dict[str, Any]
    athena: dict[str, Any]
    daedalus: dict[str, Any]
    production_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SiblingInstantRouter:
    """Package the same post-batch market instant for every sibling boundary.

    NEXUS only packages ingredients. It does not create ATHENA WorldState, ARGUS
    trade/depth truth, DAEDALUS promotion decisions, or production authorization.
    """

    @staticmethod
    def _hash(payload: Mapping[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def package_instant(
        self,
        instant: ReplayInstant,
        *,
        manifests: Mapping[str, StreamManifest],
        factors: Mapping[str, float],
        topology: Mapping[str, Any],
        quality: Mapping[str, float],
        ood: Mapping[str, float] | None = None,
        ingested_ns: int | None = None,
        factor_lineage: list[dict[str, Any]] | None = None,
        factor_derivations: list[DerivationRecord] | None = None,
        derivation: DerivationRecord | None = None,
        derivation_sequence: int = 0,
        source_health: SourceHealthPlane | Mapping[str, Any] | None = None,
    ) -> SiblingInstantBundle:
        """Canonical route for a validated atomic replay instant."""
        return self.package(
            batch=instant.batch,
            state=instant.state,
            manifests=manifests,
            factors=factors,
            topology=topology,
            quality=quality,
            ood=ood,
            ingested_ns=ingested_ns,
            factor_lineage=factor_lineage,
            factor_derivations=factor_derivations,
            derivation=derivation,
            derivation_sequence=derivation_sequence,
            source_health=source_health,
        )

    def package(
        self,
        *,
        batch: ReplayBatch,
        state: StatePacket,
        manifests: Mapping[str, StreamManifest],
        factors: Mapping[str, float],
        topology: Mapping[str, Any],
        quality: Mapping[str, float],
        ood: Mapping[str, float] | None = None,
        ingested_ns: int | None = None,
        factor_lineage: list[dict[str, Any]] | None = None,
        factor_derivations: list[DerivationRecord] | None = None,
        derivation: DerivationRecord | None = None,
        derivation_sequence: int = 0,
        source_health: SourceHealthPlane | Mapping[str, Any] | None = None,
    ) -> SiblingInstantBundle:
        if state.decision_ns != batch.visible_ns:
            raise ValueError("state and replay batch must describe the same visibility instant")
        if state.batch_size != len(batch.events):
            raise ValueError("state batch_size does not match replay batch")
        if not state.frame_hash:
            raise ValueError("state must carry a deterministic frame_hash")

        derivations = list(factor_derivations or [])
        if derivation is not None and all(d.derivation_hash != derivation.derivation_hash for d in derivations):
            derivations.append(derivation)
        for d in derivations:
            if not d.verify():
                raise ValueError(f"invalid derivation record: {d.product_id}@{d.product_version}")
            if int(d.decision_ns) != int(state.decision_ns):
                raise ValueError("derivation decision_ns must match the routed market instant; atomic replay instant required")

        health_payload: dict[str, Any] | None = None
        if source_health is not None:
            if isinstance(source_health, SourceHealthPlane):
                if not source_health.verify():
                    raise ValueError("source_health plane hash verification failed")
                if int(source_health.decision_ns) != int(state.decision_ns):
                    raise ValueError("source_health decision_ns mismatch; source-health decision_ns must match the atomic replay instant")
                health_payload = json.loads(json.dumps(source_health.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False))
            else:
                plane = SourceHealthPlane.from_dict(dict(source_health))
                if not plane.verify():
                    raise ValueError("source_health plane hash/semantic verification failed")
                if int(plane.decision_ns) != int(state.decision_ns):
                    raise ValueError("source_health decision_ns mismatch; source-health decision_ns must match the atomic replay instant")
                health_payload = json.loads(json.dumps(plane.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False))

        event_lineage = [
            {
                "stream_id": e.stream_id,
                "source_sequence": e.source_sequence,
                "revision": e.revision,
                "event_ns": e.event_ns,
                "available_ns": e.available_ns,
                "source_path": e.source_path,
                "availability_basis": e.availability_basis,
            }
            for e in batch.events
        ]
        lineage = event_lineage + list(factor_lineage or []) + [
            {"kind": "nexus_derivation", **d.to_dict()} for d in derivations
        ]
        if health_payload is not None:
            lineage.append({
                "kind": "nexus_source_health_plane",
                "decision_ns": int(health_payload["decision_ns"]),
                "plane_hash": health_payload.get("plane_hash"),
                "stream_count": health_payload.get("stream_count"),
                "healthy_fraction": health_payload.get("healthy_fraction"),
                "failed_streams": list(health_payload.get("failed_streams", [])),
                "unknown_slo_streams": list(health_payload.get("unknown_slo_streams", [])),
            })
        base = market_state_packet(
            decision_ns=state.decision_ns,
            factors=dict(factors),
            topology=dict(topology),
            quality=dict(quality),
            lineage=lineage,
            frame_hash=state.frame_hash,
            ood=dict(ood or {}),
        )
        if health_payload is not None:
            base["source_health"] = health_payload

        aion_specs: dict[str, dict[str, Any]] = {}
        aion_observations: list[dict[str, Any]] = []
        athena_provenance_rows: list[dict[str, Any]] = []
        for e in batch.events:
            manifest = manifests.get(e.stream_id)
            if manifest is None:
                raise KeyError(f"missing manifest for stream {e.stream_id}")
            aion_specs[e.stream_id] = aion_source_spec(manifest)
            aion_observations.append(aion_bar_observation(e, ingested_ns=ingested_ns))
            athena_provenance_rows.append(
                athena_provenance(
                    event_time_ns=e.event_ns,
                    ingestion_time_ns=max(
                        int(e.available_ns if e.available_ns is not None else e.event_ns),
                        int(ingested_ns if ingested_ns is not None else (e.available_ns if e.available_ns is not None else e.event_ns)),
                    ),
                    source_id=e.stream_id,
                    representation_id=manifest.identity.representation,
                    version="nexus-v0.3.0",
                    lineage_id=manifest.identity.raw_sha256,
                    quality_flags=e.quality_flags,
                )
            )

        argus_features = [
            argus_candle_proxy_feature(
                name=f"nexus.factor.{name}",
                value=float(value),
                event_ns=state.decision_ns,
                source_id=f"NEXUS:{state.frame_hash}",
                reason="NEXUS CSV/market-context derived factor; never trade/depth truth",
            )
            for name, value in sorted(factors.items())
        ]

        derivation_specs = [
            aion_derivation_source_spec(
                product_id=d.product_id,
                product_version=d.product_version,
                spec_hash=d.spec_hash,
                code_version=d.code_version,
            )
            for d in derivations
        ]
        derivation_observations = [
            aion_derivation_observation(
                d,
                sequence=(int(derivation_sequence) + i) if derivation is d and d is not None else None,
                ingested_ns=ingested_ns,
            )
            for i, d in enumerate(derivations)
        ]
        typed_health = source_health if isinstance(source_health, SourceHealthPlane) else None
        health_specs = [aion_source_health_spec(plane_hash=typed_health.plane_hash)] if typed_health is not None else []
        health_observations = [aion_source_health_observation(typed_health, ingested_ns=ingested_ns)] if typed_health is not None else []
        aion_source_rows = [aion_specs[k] for k in sorted(aion_specs)] + derivation_specs + health_specs
        aion_all_observations = aion_observations + derivation_observations + health_observations
        derivation_hashes = [d.derivation_hash for d in derivations]

        aion_payload = {
            "decision_ns": state.decision_ns,
            "frame_hash": state.frame_hash,
            "source_health": health_payload,
            "source_specs": aion_source_rows,
            "observations": aion_all_observations,
            "derivation_source_specs": derivation_specs,
            "derivation_observations": derivation_observations,
            "derivation_hash": derivation.derivation_hash if derivation is not None else (derivation_hashes[0] if len(derivation_hashes) == 1 else None),
            "derivation_hashes": derivation_hashes,
            "source_health_plane_hash": health_payload.get("plane_hash") if health_payload is not None else None,
            "production_authorized": False,
        }
        argus_payload = {
            **for_argus(base),
            "source_health": health_payload,
            "features": argus_features,
            "same_instant_batch_size": len(batch.events),
        }
        athena_payload = {
            **for_athena(base),
            "source_health": health_payload,
            "provenance": athena_provenance_rows,
            "same_instant_batch_size": len(batch.events),
        }
        daedalus_payload = daedalus_candidate(
            {
                "kind": "nexus_market_instant",
                "decision_ns": state.decision_ns,
                "frame_hash": state.frame_hash,
                "factors": dict(factors),
                "topology": dict(topology),
                "quality": dict(quality),
                "ood": dict(ood or {}),
                "lineage": lineage,
                "derivation_hash": aion_payload["derivation_hash"],
                "derivation_hashes": derivation_hashes,
                "source_health": health_payload,
            }
        )

        hash_payload = {
            "decision_ns": state.decision_ns,
            "frame_hash": state.frame_hash,
            "aion": aion_payload,
            "argus": argus_payload,
            "athena": athena_payload,
            "daedalus": daedalus_payload,
            "production_authorized": False,
        }
        bundle_hash = self._hash(hash_payload)
        return SiblingInstantBundle(
            decision_ns=state.decision_ns,
            frame_hash=state.frame_hash,
            bundle_hash=bundle_hash,
            aion=aion_payload,
            argus=argus_payload,
            athena=athena_payload,
            daedalus=daedalus_payload,
            production_authorized=False,
        )
