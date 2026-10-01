from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
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

# Path-independent NEXUS v1.16 sibling contract snapshot (ADR 0005). This is the
# reviewed current contract after AION's causal evidence hardening and explicit
# derived_at_decision semantics.
NEXUS_V116_CONTRACT_SNAPSHOT_HASH = "65cba148bc5df86bd4b660ba15b14e6c58c113fa00fecdf3e22ea745a13ffe9a"

# Historical pins remain accepted only for the exact recorded bundles that were
# produced under them. Fresh bundles must use the current v1.16 identity.
CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH = NEXUS_V116_CONTRACT_SNAPSHOT_HASH
PINNED_NEXUS_CONTRACT_SNAPSHOT_HASHES = frozenset({
    NEXUS_V03_CONTRACT_SNAPSHOT_HASH,
    NEXUS_V115_CONTRACT_SNAPSHOT_HASH,
    NEXUS_V116_CONTRACT_SNAPSHOT_HASH,
})
HISTORICAL_BUNDLE_HASHES_BY_CONTRACT = {
    NEXUS_V03_CONTRACT_SNAPSHOT_HASH: frozenset({
        "f750e97f123be8419a252d3f6810db66efb6427ff9f78483e74cea2a818d7373",
    }),
    NEXUS_V115_CONTRACT_SNAPSHOT_HASH: frozenset({
        "f5ed5c3b161b8403162383081c0ad1155242a802981788016e76dd7d8f3fcffd",
    }),
}
RECORDED_HISTORICAL_CONTRACT_BY_BUNDLE_HASH = {
    bundle_hash: contract_hash
    for contract_hash, bundle_hashes in HISTORICAL_BUNDLE_HASHES_BY_CONTRACT.items()
    for bundle_hash in bundle_hashes
}


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


_TOP_LEVEL_KEYS = frozenset({
    "decision_ns", "frame_hash", "bundle_hash", "aion", "argus", "athena",
    "daedalus", "production_authorized",
})


def _recompute_bundle_hash(payload: Mapping[str, Any]) -> str:
    if set(payload) != _TOP_LEVEL_KEYS:
        missing = sorted(_TOP_LEVEL_KEYS - set(payload))
        extra = sorted(set(payload) - _TOP_LEVEL_KEYS)
        raise ValueError(f"NEXUS bundle top-level shape mismatch; missing={missing}, extra={extra}")
    unsigned = {key: payload[key] for key in _TOP_LEVEL_KEYS if key != "bundle_hash"}
    try:
        raw = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise ValueError("NEXUS bundle must be finite canonical JSON") from exc
    return hashlib.sha256(raw).hexdigest()


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


def _validate_v116_aion_semantics(aion: Mapping[str, Any]) -> None:
    specs_raw = aion.get("source_specs")
    observations = aion.get("observations")
    if not isinstance(specs_raw, list) or not isinstance(observations, list):
        raise ValueError("v1.16 AION payload requires source_specs and observations arrays")
    specs: dict[str, Mapping[str, Any]] = {}
    for raw in specs_raw:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("source_id"), str):
            raise ValueError("v1.16 AION source spec is malformed")
        specs[raw["source_id"]] = raw
    for observation in observations:
        if not isinstance(observation, Mapping):
            raise ValueError("v1.16 AION observation is malformed")
        source_id = observation.get("source_id")
        spec = specs.get(source_id)
        if spec is None:
            raise ValueError("v1.16 AION observation has no matching source spec")
        basis = observation.get("availability_basis")
        flags = observation.get("quality_flags", [])
        if spec.get("origin") == "nexus_derived":
            if (
                observation.get("kind") != "context"
                or basis != "derived_at_decision"
                or observation.get("event_ns") != observation.get("available_ns")
                or (isinstance(flags, list) and "synthetic" in flags)
            ):
                raise ValueError("v1.16 nexus_derived AION context must use derived_at_decision semantics")
        elif basis == "derived_at_decision":
            raise ValueError("v1.16 derived_at_decision requires a nexus_derived source")


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
    expected_bundle_hash = _recompute_bundle_hash(payload)
    if bundle_hash != expected_bundle_hash:
        raise ValueError("bundle_hash does not match canonical NEXUS bundle content")
    recorded_contract = RECORDED_HISTORICAL_CONTRACT_BY_BUNDLE_HASH.get(bundle_hash)
    if recorded_contract is not None and contract_snapshot_hash != recorded_contract:
        raise ValueError("recorded historical bundle must retain its original contract identity")
    if contract_snapshot_hash != CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH:
        allowed = HISTORICAL_BUNDLE_HASHES_BY_CONTRACT.get(contract_snapshot_hash, frozenset())
        if bundle_hash not in allowed:
            raise ValueError("historical contract identity only replays recorded historical bundles; bind new bundles under the current pin")

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
    if contract_snapshot_hash == NEXUS_V116_CONTRACT_SNAPSHOT_HASH:
        _validate_v116_aion_semantics(aion)

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

