from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..contracts import FailureCase
from ..sentinel.failure import bundle_validation_failure, causal_instant_failure, contract_drift_failure

# Release-pinned NEXUS v0.3 sibling contract snapshot from the recovered handoff.
# The handoff's final drift report shows this baseline has zero raw/semantic
# drift against the recovered sibling contract files. The path-bearing snapshot
# hash itself is treated as an externally supplied release identity, not
# recomputed locally from filesystem paths.
NEXUS_V03_CONTRACT_SNAPSHOT_HASH = "1119ef3d9b561dc89668a9768893a2b1ab09cd542ffd1d7a02dd73f5a81388a2"

# Path-independent NEXUS v1.15 sibling contract snapshot (ADR 0004): recorded with
# repo-relative paths; differs from the v0.3 release only by the additive DAEDALUS
# NEXUS-handoff receiver API (reviewed: 166 lines added, none changed).
NEXUS_V115_CONTRACT_SNAPSHOT_HASH = "b394df6cf80ddbac014f4024222469b169178fadd7c26f4a597aed58671b5bb3"

# Identities a caller may bind under. The v0.3 pin stays accepted so recorded
# historical bundles replay; new bundles use the current pin.
CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH = NEXUS_V115_CONTRACT_SNAPSHOT_HASH
PINNED_NEXUS_CONTRACT_SNAPSHOT_HASHES = frozenset({NEXUS_V03_CONTRACT_SNAPSHOT_HASH, NEXUS_V115_CONTRACT_SNAPSHOT_HASH})

# The v0.3 identity binds only these recorded bundles (the recovered v0.3 same-instant
# bundle), so a fresh bundle cannot be labelled with the historical contract identity.
HISTORICAL_V03_BUNDLE_HASHES = frozenset({"f750e97f123be8419a252d3f6810db66efb6427ff9f78483e74cea2a818d7373"})


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


@dataclass(frozen=True)
class NexusBundleBinding:
    decision_ns: int
    frame_hash: str
    bundle_hash: str
    contract_snapshot_hash: str
    aion: Mapping[str, Any]
    argus: Mapping[str, Any]
    athena: Mapping[str, Any]
    daedalus: Mapping[str, Any]


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} sibling payload must be a mapping")
    return value


def _reject_production_authority(name: str, payload: Mapping[str, Any]) -> None:
    if payload.get("production_authorized") is True:
        raise ValueError(f"{name} production_authorized must remain false")


def validate_nexus_bundle(
    payload: Mapping[str, Any],
    contract_snapshot_hash: str,
) -> NexusBundleBinding:
    if contract_snapshot_hash not in PINNED_NEXUS_CONTRACT_SNAPSHOT_HASHES:
        raise ValueError("NEXUS contract snapshot hash mismatch")
    if payload.get("production_authorized") is not False:
        raise ValueError("outer production_authorized must be false")

    decision_ns = payload.get("decision_ns")
    if not isinstance(decision_ns, int):
        raise ValueError("decision_ns must be an integer")

    frame_hash = payload.get("frame_hash")
    if not _is_sha256(frame_hash):
        raise ValueError("frame_hash must be a SHA-256 hex digest")

    bundle_hash = payload.get("bundle_hash")
    if not _is_sha256(bundle_hash):
        raise ValueError("bundle_hash must be a SHA-256 hex digest")
    if contract_snapshot_hash == NEXUS_V03_CONTRACT_SNAPSHOT_HASH and bundle_hash not in HISTORICAL_V03_BUNDLE_HASHES:
        raise ValueError("v0.3 contract identity only replays recorded historical bundles; bind new bundles under the current pin")

    aion = _require_mapping(payload, "aion")
    argus = _require_mapping(payload, "argus")
    athena = _require_mapping(payload, "athena")
    daedalus = _require_mapping(payload, "daedalus")
    for name, sibling_payload in (
        ("aion", aion),
        ("argus", argus),
        ("athena", athena),
        ("daedalus", daedalus),
    ):
        _reject_production_authority(name, sibling_payload)

    return NexusBundleBinding(
        decision_ns=decision_ns,
        frame_hash=frame_hash,
        bundle_hash=bundle_hash,
        contract_snapshot_hash=contract_snapshot_hash,
        aion=aion,
        argus=argus,
        athena=athena,
        daedalus=daedalus,
    )

def validate_sibling_decision_instants(binding: NexusBundleBinding) -> None:
    checks = (
        ("AION", binding.aion.get("decision_ns")),
        ("ARGUS", binding.argus.get("decision_ns")),
        ("ATHENA", binding.athena.get("decision_ns")),
    )
    for name, observed in checks:
        if observed != binding.decision_ns:
            raise ValueError(f"{name} decision_ns mismatch: expected {binding.decision_ns}, observed {observed!r}")
    candidate = binding.daedalus.get("candidate")
    if not isinstance(candidate, Mapping):
        raise ValueError("DAEDALUS candidate must be a mapping")
    observed = candidate.get("decision_ns")
    if observed != binding.decision_ns:
        raise ValueError(f"DAEDALUS decision_ns mismatch: expected {binding.decision_ns}, observed {observed!r}")


def try_bind_nexus_bundle(
    payload: Mapping[str, Any],
    contract_snapshot_hash: str,
) -> NexusBundleBinding | FailureCase:
    decision_instant = str(payload.get("decision_ns", "UNKNOWN"))
    if contract_snapshot_hash not in PINNED_NEXUS_CONTRACT_SNAPSHOT_HASHES:
        return contract_drift_failure(
            expected_hash=CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH,
            observed_hash=contract_snapshot_hash,
            decision_instant=decision_instant,
        )
    try:
        binding = validate_nexus_bundle(payload, contract_snapshot_hash)
    except ValueError as exc:
        return bundle_validation_failure(
            expected_hash=contract_snapshot_hash,
            observed_hash=contract_snapshot_hash,
            decision_instant=decision_instant,
            details=str(exc),
        )
    try:
        validate_sibling_decision_instants(binding)
    except ValueError as exc:
        return causal_instant_failure(
            contract_hash=contract_snapshot_hash,
            decision_instant=str(binding.decision_ns),
            details=str(exc),
        )
    return binding

