from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..contracts import ObservationEnvelope
from ..ids import canonical_json
from .nexus import NexusBundleBinding, validate_sibling_decision_instants


def _scalar(value: Any) -> str:
    if isinstance(value, str):
        return value
    return canonical_json(value)


def _flatten_prefixed(prefix: str, value: Any) -> list[tuple[str, str]]:
    if not isinstance(value, Mapping):
        return []
    rows: list[tuple[str, str]] = []
    for key, item in sorted(value.items(), key=lambda kv: str(kv[0])):
        if isinstance(item, (Mapping, list, tuple, set)):
            continue
        rows.append((f"{prefix}:{key}", _scalar(item)))
    return rows


def _source_ref(binding: NexusBundleBinding, sibling: str) -> str:
    return f"nexus-bundle:{binding.bundle_hash}:frame:{binding.frame_hash}:projection:{sibling}"


def _shared_context(payload: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    rows.extend(_flatten_prefixed("factor", payload.get("factors")))
    rows.extend(_flatten_prefixed("quality", payload.get("quality")))
    rows.extend(_flatten_prefixed("ood", payload.get("ood")))
    health = payload.get("source_health")
    if isinstance(health, Mapping):
        for key in ("plane_hash", "healthy_fraction", "stream_count"):
            if key in health and not isinstance(health[key], (Mapping, list, tuple, set)):
                rows.append((f"source_health:{key}", _scalar(health[key])))
    return rows


def _make(
    *,
    sibling: str,
    binding: NexusBundleBinding,
    evidence_tier: str,
    dimensions: list[tuple[str, str]],
) -> ObservationEnvelope:
    return ObservationEnvelope(
        sibling=sibling,
        decision_instant=str(binding.decision_ns),
        availability_state="KNOWN",
        evidence_tier=evidence_tier,
        dimensions=tuple(sorted(dimensions)),
        source_ref=_source_ref(binding, sibling),
    )


def normalize_nexus_bundle(binding: NexusBundleBinding) -> tuple[ObservationEnvelope, ...]:
    """Project a validated NEXUS same-instant bundle into PROMETHEUS evidence.

    Only semantics already present in the recovered NEXUS v0.3 payload are
    projected. No direction/regime/risk conclusion is inferred from numeric
    factors, and no sibling authority is upgraded.
    """

    aion = binding.aion
    argus = binding.argus
    athena = binding.athena
    daedalus = binding.daedalus
    candidate = daedalus.get("candidate")
    if not isinstance(candidate, Mapping):
        raise ValueError("DAEDALUS candidate must be a mapping")

    validate_sibling_decision_instants(binding)

    # NEXUS has no separate top-level factor payload in SiblingInstantBundle.
    # The DAEDALUS research candidate is explicitly kind=nexus_market_instant and
    # carries the canonical NEXUS market-state ingredients without promotion.
    nexus_dims = [
        ("candidate_kind", _scalar(candidate.get("kind"))),
        ("frame_hash", binding.frame_hash),
    ]
    nexus_dims.extend(_shared_context(candidate))

    argus_tier = argus.get("evidence_tier")
    if not isinstance(argus_tier, str) or not argus_tier:
        raise ValueError("ARGUS evidence_tier is required")
    argus_dims = [
        ("contract", _scalar(argus.get("contract"))),
        ("data_plane", _scalar(argus.get("data_plane"))),
        ("evidence_tier", argus_tier),
        ("microstructure_truth", _scalar(argus.get("microstructure_truth"))),
    ]
    argus_dims.extend(_shared_context(argus))

    athena_dims = [
        ("contract", _scalar(athena.get("contract"))),
        ("data_plane", _scalar(athena.get("data_plane"))),
        ("purpose", _scalar(athena.get("purpose"))),
        ("advisory_only", _scalar(athena.get("advisory_only"))),
    ]
    athena_dims.extend(_shared_context(athena))

    daedalus_status = daedalus.get("status")
    if daedalus_status != "RESEARCH_CANDIDATE_ONLY":
        raise ValueError("DAEDALUS status must remain RESEARCH_CANDIDATE_ONLY")
    if daedalus.get("production_authorized") is not False:
        raise ValueError("DAEDALUS production_authorized must remain false")
    daedalus_dims = [
        ("schema", _scalar(daedalus.get("schema"))),
        ("status", daedalus_status),
        ("candidate_kind", _scalar(candidate.get("kind"))),
        ("production_authorized", "false"),
    ]
    daedalus_dims.extend(_shared_context(candidate))

    return (
        _make(
            sibling="NEXUS",
            binding=binding,
            evidence_tier="NEXUS_MARKET_STATE",
            dimensions=nexus_dims,
        ),
        _make(
            sibling="ARGUS",
            binding=binding,
            evidence_tier=argus_tier,
            dimensions=argus_dims,
        ),
        _make(
            sibling="ATHENA",
            binding=binding,
            evidence_tier="ATHENA_STATE_INPUT",
            dimensions=athena_dims,
        ),
        _make(
            sibling="DAEDALUS",
            binding=binding,
            evidence_tier=daedalus_status,
            dimensions=daedalus_dims,
        ),
    )
