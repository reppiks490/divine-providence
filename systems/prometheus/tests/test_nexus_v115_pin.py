"""ADR 0005: NEXUS v1.16 current pin with immutable historical v0.3/v1.15 replay."""
import copy
import hashlib
import json
from pathlib import Path

from prometheus_loop.adapters.nexus import (
    CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH,
    NEXUS_V03_CONTRACT_SNAPSHOT_HASH,
    NEXUS_V115_CONTRACT_SNAPSHOT_HASH,
    NEXUS_V116_CONTRACT_SNAPSHOT_HASH,
    PINNED_NEXUS_CONTRACT_SNAPSHOT_HASHES,
    NexusBundleBinding,
    try_bind_nexus_bundle,
    validate_nexus_bundle,
)
from prometheus_loop.adapters.siblings import normalize_nexus_bundle
from prometheus_loop.contracts import FailureCase

FIXTURES = Path(__file__).parent / "fixtures"
V115 = FIXTURES / "nexus_v115_same_instant_bundle.json"
V03 = FIXTURES / "nexus_v03_same_instant_bundle.json"
TOP_LEVEL = {
    "decision_ns", "frame_hash", "bundle_hash", "aion", "argus", "athena",
    "daedalus", "production_authorized",
}


def _load(path):
    return json.loads(path.read_text())


def _rehash(payload):
    unsigned = {k: payload[k] for k in TOP_LEVEL if k != "bundle_hash"}
    raw = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    payload["bundle_hash"] = hashlib.sha256(raw).hexdigest()
    return payload


def _upgrade_aion_v116_semantics(payload):
    specs = {x["source_id"]: x for x in payload["aion"]["source_specs"]}
    for observation in payload["aion"]["observations"]:
        if specs[observation["source_id"]].get("origin") == "nexus_derived":
            observation["availability_basis"] = "derived_at_decision"
            observation["quality_flags"] = [x for x in observation.get("quality_flags", []) if x != "synthetic"]
    return payload


def test_pinned_identities_include_current_v116_and_two_historical_snapshots():
    assert PINNED_NEXUS_CONTRACT_SNAPSHOT_HASHES == {
        NEXUS_V03_CONTRACT_SNAPSHOT_HASH,
        NEXUS_V115_CONTRACT_SNAPSHOT_HASH,
        NEXUS_V116_CONTRACT_SNAPSHOT_HASH,
    }
    assert CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH == NEXUS_V116_CONTRACT_SNAPSHOT_HASH


def test_historical_v115_bundle_still_replays_under_its_original_pin():
    binding = validate_nexus_bundle(_load(V115), NEXUS_V115_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(binding, NexusBundleBinding)
    observations = normalize_nexus_bundle(binding)
    assert {o.sibling for o in observations} == {"NEXUS", "ARGUS", "ATHENA", "DAEDALUS"}


def test_historical_v03_bundle_still_replays_under_its_release_pin():
    assert isinstance(validate_nexus_bundle(_load(V03), NEXUS_V03_CONTRACT_SNAPSHOT_HASH), NexusBundleBinding)


def test_recorded_historical_bundle_cannot_be_relabelled_with_current_identity():
    result = try_bind_nexus_bundle(_load(V115), CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert "original contract identity" in result.details


def test_fresh_bundle_cannot_be_labelled_with_historical_v115_identity():
    payload = _upgrade_aion_v116_semantics(copy.deepcopy(_load(V115)))
    payload["athena"]["purpose"] = "fresh-current-fixture"
    _rehash(payload)
    result = try_bind_nexus_bundle(payload, NEXUS_V115_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert "recorded historical bundles" in result.details


def test_current_pin_rejects_old_synthetic_label_for_nexus_derived_context():
    payload = copy.deepcopy(_load(V115))
    payload["athena"]["purpose"] = "fresh-current-fixture"
    _rehash(payload)
    result = try_bind_nexus_bundle(payload, CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert "derived_at_decision" in result.details


def test_bundle_hash_is_bound_to_canonical_bundle_content():
    payload = _load(V115)
    payload["argus"]["microstructure_truth"] = True
    result = try_bind_nexus_bundle(payload, NEXUS_V115_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert "bundle_hash" in result.details


def test_unpinned_identity_is_quarantined_against_current_v116_pin():
    result = try_bind_nexus_bundle(_load(V115), "f" * 64)
    assert isinstance(result, FailureCase)
    assert result.failure_type == "CONTRACT_DRIFT"
    assert result.expected_contract_hash == CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH


def test_v116_bundle_still_rejects_production_authority_after_valid_rehash():
    payload = _upgrade_aion_v116_semantics(copy.deepcopy(_load(V115)))
    payload["athena"]["purpose"] = "fresh-current-fixture"
    payload["daedalus"]["production_authorized"] = True
    _rehash(payload)
    result = try_bind_nexus_bundle(payload, CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert "production_authorized" in result.details



def test_v116_rejects_non_mapping_sibling_after_valid_rehash():
    payload = _upgrade_aion_v116_semantics(copy.deepcopy(_load(V115)))
    payload["athena"]["purpose"] = "fresh-current-fixture"
    payload["argus"] = []
    _rehash(payload)
    result = try_bind_nexus_bundle(payload, CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert "argus" in result.details
