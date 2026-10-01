import hashlib
import json
from pathlib import Path

import pytest

from prometheus_loop.adapters.nexus import CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH, NEXUS_V03_CONTRACT_SNAPSHOT_HASH
from prometheus_loop.contracts import LoopKind, RunStatus
from prometheus_loop.fixtures import sample_candidate_profile, sample_plugins
from prometheus_loop.memory.store import ResearchMemory
from prometheus_loop.orchestration.loop import HostPluginResult, NexusRunInput, PrometheusLoop

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


def _completed(plugin_id):
    return HostPluginResult(
        plugin_id=plugin_id,
        success=True,
        input_fingerprint=f"input:{plugin_id}",
        output_fingerprint=f"output:{plugin_id}",
    )


def _run_input(payload, contract_snapshot_hash=NEXUS_V03_CONTRACT_SNAPSHOT_HASH):
    return NexusRunInput(
        run_kind=LoopKind.FORGE,
        objective="research sibling contract disagreement with source-backed architecture validation",
        bundle=payload,
        contract_snapshot_hash=contract_snapshot_hash,
        plugin_inventory=sample_plugins(),
        plugin_results=(_completed("deep-research"), _completed("exa")),
        candidate_profile=sample_candidate_profile(),
        baseline_metrics=(("score", 0.50), ("drawdown", 0.20)),
        candidate_metrics=(("score", 0.61), ("drawdown", 0.18)),
    )


def test_nexus_bundle_runs_through_existing_research_loop(tmp_path):
    payload = _current_payload()
    payload["athena"]["factors"]["risk"] = 0.9
    _rehash(payload)
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    loop = PrometheusLoop(memory)

    result = loop.run_nexus(_run_input(payload, CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH))

    assert result.status is RunStatus.RESEARCH_COMPLETE
    assert any(case.dimension == "factor:risk" for case in result.disagreements)
    assert result.result.artifact_id
    assert memory.find_by_id(result.plugin_audit.artifact_id)
    for observation_id in result.observation_ids:
        assert memory.find_by_id(observation_id)
    assert result.provenance_manifest_id is not None
    manifest = memory.find_by_id(result.provenance_manifest_id)["payload"]
    assert manifest["source_contract_ids"] == [f"nexus-contract:{CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH}"]
    assert manifest["parent_manifest_ids"] == []


def test_clean_nexus_bundle_does_not_fabricate_disagreement(tmp_path):
    loop = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl"))
    with pytest.raises(ValueError, match="no disagreement case"):
        loop.run_nexus(_run_input(_payload()))

from prometheus_loop.attestation import PluginAttestationPolicy


def test_nexus_run_propagates_strict_attestation_policy(tmp_path):
    payload = _current_payload()
    payload["athena"]["factors"]["risk"] = 0.9
    _rehash(payload)
    base = _run_input(payload, CURRENT_NEXUS_CONTRACT_SNAPSHOT_HASH)
    strict = NexusRunInput(**{**base.__dict__, "plugin_attestation_policy": PluginAttestationPolicy.REQUIRE_VERIFIED})
    result = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl")).run_nexus(strict)
    assert result.status is RunStatus.DEGRADED_RESEARCH
    assert result.promotion_packet is None
