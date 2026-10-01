import copy
import hashlib
import json
from pathlib import Path

import pytest

from prometheus_loop.adapters.nexus import (
    CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH,
    NEXUS_V03_CONTRACT_SNAPSHOT_HASH,
    validate_nexus_bundle,
)
from prometheus_loop.adapters.siblings import normalize_nexus_bundle

FIXTURE = Path(__file__).parent / "fixtures" / "nexus_v03_same_instant_bundle.json"


def _payload():
    return json.loads(FIXTURE.read_text())


def _current_payload():
    payload = _payload()
    specs = {row["source_id"]: row for row in payload["aion"]["source_specs"]}
    for observation in payload["aion"]["observations"]:
        if specs[observation["source_id"]].get("origin") == "nexus_derived":
            observation["availability_basis"] = "derived_at_decision"
            observation["quality_flags"] = [
                flag for flag in observation.get("quality_flags", [])
                if flag != "synthetic"
            ]
    return payload


def _rehash(payload):
    unsigned = {key: value for key, value in payload.items() if key != "bundle_hash"}
    raw = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    payload["bundle_hash"] = hashlib.sha256(raw).hexdigest()
    return payload


def _observations(payload=None, contract_snapshot_hash=NEXUS_V03_CONTRACT_SNAPSHOT_HASH):
    binding = validate_nexus_bundle(payload or _payload(), contract_snapshot_hash)
    return normalize_nexus_bundle(binding)


def test_normalizes_recovered_bundle_without_inventing_authority():
    observations = _observations()
    assert [o.sibling for o in observations] == ["NEXUS", "ARGUS", "ATHENA", "DAEDALUS"]
    assert {o.decision_instant for o in observations} == {"160"}
    assert all(o.availability_state == "KNOWN" for o in observations)
    assert all("f750e97f123be8419a252d3f6810db66efb6427ff9f78483e74cea2a818d7373" in o.source_ref for o in observations)
    assert all("b9056e25cf6474002399876f4b8290cf0b8747d2c9ae5b149898ccff07c9a199" in o.source_ref for o in observations)

    by_name = {o.sibling: o for o in observations}
    argus = by_name["ARGUS"]
    assert argus.evidence_tier == "CANDLE_PROXY"
    assert dict(argus.dimensions)["evidence_tier"] == "CANDLE_PROXY"
    assert dict(argus.dimensions)["microstructure_truth"] == "false"

    athena = by_name["ATHENA"]
    assert dict(athena.dimensions)["purpose"] == "state_input"
    assert dict(athena.dimensions)["advisory_only"] == "true"

    daedalus = by_name["DAEDALUS"]
    assert daedalus.evidence_tier == "RESEARCH_CANDIDATE_ONLY"
    assert dict(daedalus.dimensions)["status"] == "RESEARCH_CANDIDATE_ONLY"
    assert dict(daedalus.dimensions)["production_authorized"] == "false"


def test_shared_numeric_context_is_projected_with_common_dimension_names():
    observations = _observations()
    by_name = {o.sibling: dict(o.dimensions) for o in observations}
    for sibling in ("NEXUS", "ARGUS", "ATHENA", "DAEDALUS"):
        assert by_name[sibling]["factor:risk"] == "0.2"
        assert by_name[sibling]["factor:tech"] == "0.4"
        assert by_name[sibling]["quality:coverage"] == "1.0"
        assert by_name[sibling]["ood:novelty"] == "0.1"


def test_rejects_sibling_decision_instant_mismatch():
    for sibling, path in (
        ("argus", ("decision_ns",)),
        ("athena", ("decision_ns",)),
        ("daedalus", ("candidate", "decision_ns")),
    ):
        payload = _current_payload()
        target = payload[sibling]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = 159
        _rehash(payload)
        binding = validate_nexus_bundle(payload, CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
        with pytest.raises(ValueError, match="decision_ns"):
            normalize_nexus_bundle(binding)


def test_missing_optional_comparison_dimension_remains_missing():
    payload = _current_payload()
    del payload["athena"]["ood"]["novelty"]
    _rehash(payload)
    observations = _observations(payload, CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
    athena = next(o for o in observations if o.sibling == "ATHENA")
    assert "ood:novelty" not in dict(athena.dimensions)
