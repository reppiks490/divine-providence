import copy
import json
from pathlib import Path

import pytest

from prometheus_loop.adapters.nexus import (
    NEXUS_V03_CONTRACT_SNAPSHOT_HASH,
    NexusBundleBinding,
    validate_nexus_bundle,
)

FIXTURE = Path(__file__).parent / "fixtures" / "nexus_v03_same_instant_bundle.json"


def _payload():
    return json.loads(FIXTURE.read_text())


def test_accepts_recovered_nexus_v03_bundle():
    payload = _payload()
    binding = validate_nexus_bundle(payload, NEXUS_V03_CONTRACT_SNAPSHOT_HASH)
    assert isinstance(binding, NexusBundleBinding)
    assert binding.decision_ns == 160
    assert binding.frame_hash == payload["frame_hash"]
    assert binding.bundle_hash == payload["bundle_hash"]
    assert binding.contract_snapshot_hash == NEXUS_V03_CONTRACT_SNAPSHOT_HASH
    assert binding.aion["production_authorized"] is False
    assert binding.argus["microstructure_truth"] is False
    assert binding.athena["advisory_only"] is True
    assert binding.daedalus["status"] == "RESEARCH_CANDIDATE_ONLY"


def test_rejects_missing_frame_hash():
    payload = _payload()
    payload.pop("frame_hash")
    with pytest.raises(ValueError, match="frame_hash"):
        validate_nexus_bundle(payload, NEXUS_V03_CONTRACT_SNAPSHOT_HASH)


def test_rejects_production_authorization_anywhere_explicit():
    payload = _payload()
    payload["production_authorized"] = True
    with pytest.raises(ValueError, match="production_authorized"):
        validate_nexus_bundle(payload, NEXUS_V03_CONTRACT_SNAPSHOT_HASH)

    for sibling in ("aion", "daedalus"):
        bad = _payload()
        bad[sibling]["production_authorized"] = True
        with pytest.raises(ValueError, match="production_authorized"):
            validate_nexus_bundle(bad, NEXUS_V03_CONTRACT_SNAPSHOT_HASH)


def test_rejects_wrong_contract_snapshot_hash():
    with pytest.raises(ValueError, match="contract snapshot"):
        validate_nexus_bundle(_payload(), "0" * 64)


def test_rejects_non_mapping_sibling_payload():
    payload = _payload()
    payload["argus"] = []
    with pytest.raises(ValueError, match="argus"):
        validate_nexus_bundle(payload, NEXUS_V03_CONTRACT_SNAPSHOT_HASH)
