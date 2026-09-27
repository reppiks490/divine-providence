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


def test_contract_hash_drift_returns_failure_case_and_no_binding():
    observed = "0" * 64
    result = try_bind_nexus_bundle(_payload(), observed)
    assert isinstance(result, FailureCase)
    assert result.failure_type == "CONTRACT_DRIFT"
    assert result.source_system == "NEXUS"
    # ADR 0004: drift is reported against the current pin (v1.15 path-independent snapshot).
    assert result.expected_contract_hash == CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH
    assert result.observed_contract_hash == observed
    assert result.decision_instant == "160"
    assert result.artifact_id.startswith("failure:")


def test_same_instant_mismatch_returns_failure_case_and_stops_before_forge():
    payload = _payload()
    payload["athena"]["decision_ns"] = 159
    result = try_bind_nexus_bundle(payload, NEXUS_V03_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(result, FailureCase)
    assert result.failure_type == "CAUSAL_INSTANT_MISMATCH"
    assert result.source_system == "NEXUS"
    assert result.decision_instant == "160"
    assert "ATHENA" in result.details
