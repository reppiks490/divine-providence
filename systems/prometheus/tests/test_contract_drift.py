import hashlib
import json
from pathlib import Path

from prometheus_loop.adapters.nexus import (
    CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH,
    NEXUS_V03_CONTRACT_SNAPSHOT_HASH,
    try_bind_nexus_bundle,
)
from prometheus_loop.contracts import FailureCase

FIXTURE = Path(__file__).parent / "fixtures" / "nexus_v03_same_instant_bundle.json"


def _payload():
    return json.loads(FIXTURE.read_text())


def _rehash(payload):
    unsigned = {k: v for k, v in payload.items() if k != "bundle_hash"}
    raw = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    payload["bundle_hash"] = hashlib.sha256(raw).hexdigest()
    return payload


def test_contract_hash_drift_returns_failure_case_and_no_binding():
    observed = "0" * 64
    result = try_bind_nexus_bundle(_payload(), observed)
    assert isinstance(result, FailureCase)
    assert result.failure_type == "CONTRACT_DRIFT"
    assert result.source_system == "NEXUS"
    # ADR 0005: drift is reported against the current v1.16 causal snapshot.
    assert result.expected_contract_hash == CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH
    assert result.observed_contract_hash == observed
    assert result.decision_instant == "160"
    assert result.artifact_id.startswith("failure:")


def test_same_instant_mismatch_returns_failure_case_and_stops_before_forge():
    payload = _payload()
    payload["athena"]["decision_ns"] = 159
    specs = {x["source_id"]: x for x in payload["aion"]["source_specs"]}
    for observation in payload["aion"]["observations"]:
        if specs[observation["source_id"]].get("origin") == "nexus_derived":
            observation["availability_basis"] = "derived_at_decision"
            observation["quality_flags"] = [x for x in observation.get("quality_flags", []) if x != "synthetic"]
    _rehash(payload)
    # This is now a fresh/current-shape bundle; the hash is valid, so the
    # decision-instant mismatch must still fail at the causal gate.
    result = try_bind_nexus_bundle(payload, CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert result.failure_type == "CAUSAL_INSTANT_MISMATCH"
    assert result.source_system == "NEXUS"
    assert result.decision_instant == "160"
    assert "ATHENA" in result.details
