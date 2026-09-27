"""ADR 0004: NEXUS v1.15 path-independent contract pin alongside the v0.3 release pin."""
import json
from pathlib import Path

from prometheus_loop.adapters.nexus import (
    CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH,
    NEXUS_V03_CONTRACT_SNAPSHOT_HASH,
    NEXUS_V115_CONTRACT_SNAPSHOT_HASH,
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


def _load(path):
    return json.loads(path.read_text())


def test_pinned_identities_are_exactly_the_two_reviewed_snapshots():
    assert PINNED_NEXUS_CONTRACT_SNAPSHOT_HASHES == {NEXUS_V03_CONTRACT_SNAPSHOT_HASH, NEXUS_V115_CONTRACT_SNAPSHOT_HASH}
    assert CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH == NEXUS_V115_CONTRACT_SNAPSHOT_HASH


def test_fresh_v115_bundle_binds_and_normalizes_without_authority():
    binding = try_bind_nexus_bundle(_load(V115), CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(binding, NexusBundleBinding)
    assert binding.contract_snapshot_hash == NEXUS_V115_CONTRACT_SNAPSHOT_HASH
    observations = normalize_nexus_bundle(binding)
    assert {o.sibling for o in observations} == {"NEXUS", "ARGUS", "ATHENA", "DAEDALUS"}
    assert {o.decision_instant for o in observations} == {str(binding.decision_ns)}
    argus = next(o for o in observations if o.sibling == "ARGUS")
    assert argus.evidence_tier == "CANDLE_PROXY"
    assert dict(argus.dimensions)["microstructure_truth"] == "false"


def test_historical_v03_bundle_still_replays_under_its_release_pin():
    assert isinstance(validate_nexus_bundle(_load(V03), NEXUS_V03_CONTRACT_SNAPSHOT_HASH), NexusBundleBinding)


def test_fresh_bundle_cannot_be_labelled_with_the_historical_v03_identity():
    result = try_bind_nexus_bundle(_load(V115), NEXUS_V03_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert "recorded historical bundles" in result.details


def test_unpinned_identity_is_quarantined_against_the_current_pin():
    result = try_bind_nexus_bundle(_load(V115), "f" * 64)
    assert isinstance(result, FailureCase)
    assert result.failure_type == "CONTRACT_DRIFT"
    assert result.expected_contract_hash == CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH


def test_v115_bundle_still_rejects_production_authority():
    payload = _load(V115)
    payload["daedalus"]["production_authorized"] = True
    result = try_bind_nexus_bundle(payload, CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert "production_authorized" in result.details
