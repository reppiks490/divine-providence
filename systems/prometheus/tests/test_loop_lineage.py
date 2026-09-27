import json

import pytest
from pathlib import Path

from prometheus_loop.adapters.nexus import NEXUS_V03_CONTRACT_SNAPSHOT_HASH
from prometheus_loop.contracts import LoopKind
from prometheus_loop.fixtures import sample_candidate_profile, sample_observations, sample_plugins
from prometheus_loop.memory.store import ResearchMemory
from prometheus_loop.orchestration.loop import HostPluginResult, NexusRunInput, PrometheusLoop, RunInput

FIXTURE = Path(__file__).parent / "fixtures" / "nexus_v03_same_instant_bundle.json"


def _completed(plugin_id: str):
    return HostPluginResult(
        plugin_id=plugin_id,
        success=True,
        input_fingerprint=f"input:{plugin_id}",
        output_fingerprint=f"output:{plugin_id}",
    )


def _plugins():
    return sample_plugins()


def test_loop_persists_diagnoses_and_lineage(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    run = PrometheusLoop(memory).run(
        RunInput(
            run_kind=LoopKind.FORGE,
            objective="research architecture validation with source-backed analysis",
            observations=sample_observations(),
            plugin_inventory=_plugins(),
            plugin_results=(_completed("deep-research"), _completed("exa")),
            candidate_profile=sample_candidate_profile(),
            baseline_metrics=(("score", 0.50),),
            candidate_metrics=(("score", 0.60),),
            contract_fingerprints=(("ATHENA", "athena-v1"),),
        )
    )
    assert run.diagnoses
    for diagnosis in run.diagnoses:
        assert memory.find_by_id(diagnosis.artifact_id)
    assert memory.find_by_id(run.lineage_manifest_id)
    assert run.promotion_packet is not None
    assert run.promotion_packet.lineage_manifest_id == run.lineage_manifest_id


def test_nexus_run_lineage_binds_nexus_contract_fingerprint(tmp_path):
    payload = json.loads(FIXTURE.read_text())
    payload["athena"]["factors"]["risk"] = 0.9
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    run = PrometheusLoop(memory).run_nexus(
        NexusRunInput(
            run_kind=LoopKind.FORGE,
            objective="research sibling contract disagreement with source-backed architecture validation",
            bundle=payload,
            contract_snapshot_hash=NEXUS_V03_CONTRACT_SNAPSHOT_HASH,
            plugin_inventory=_plugins(),
            plugin_results=(_completed("deep-research"), _completed("exa")),
            candidate_profile=sample_candidate_profile(),
            baseline_metrics=(("score", 0.50),),
            candidate_metrics=(("score", 0.60),),
        )
    )
    record = memory.find_by_id(run.lineage_manifest_id)
    fingerprints = {name: value for name, value in record["payload"]["contract_fingerprints"]}
    assert fingerprints["NEXUS"] == NEXUS_V03_CONTRACT_SNAPSHOT_HASH
    assert fingerprints["plugin:deep-research"]
    assert fingerprints["plugin:exa"]


def test_stale_lineage_blocks_daedalus_handoff(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    run = PrometheusLoop(memory).run(
        RunInput(
            run_kind=LoopKind.FORGE,
            objective="research architecture validation with source-backed analysis",
            observations=sample_observations(),
            plugin_inventory=_plugins(),
            plugin_results=(_completed("deep-research"), _completed("exa")),
            candidate_profile=sample_candidate_profile(),
            baseline_metrics=(("score", 0.50),),
            candidate_metrics=(("score", 0.60),),
            contract_fingerprints=(("ATHENA", "athena-v1"),),
            current_contract_fingerprints=(("ATHENA", "athena-v2"),),
        )
    )
    assert run.stale_evidence_report.is_stale is True
    assert run.promotion_packet is None


def test_conflicting_explicit_plugin_contract_fingerprint_fails_closed(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    with pytest.raises(ValueError, match="conflicting contract fingerprint for plugin:exa"):
        PrometheusLoop(memory).run(
            RunInput(
                run_kind=LoopKind.FORGE,
                objective="research architecture validation with source-backed analysis",
                observations=sample_observations(),
                plugin_inventory=_plugins(),
                plugin_results=(_completed("deep-research"), _completed("exa")),
                candidate_profile=sample_candidate_profile(),
                baseline_metrics=(("score", 0.50),),
                candidate_metrics=(("score", 0.60),),
                contract_fingerprints=(("plugin:exa", "stale-or-forged-descriptor"),),
            )
        )


def test_duplicate_current_contract_overrides_fail_closed(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    with pytest.raises(ValueError, match="duplicate current contract fingerprint for ATHENA"):
        PrometheusLoop(memory).run(
            RunInput(
                run_kind=LoopKind.FORGE,
                objective="research architecture validation with source-backed analysis",
                observations=sample_observations(),
                plugin_inventory=_plugins(),
                plugin_results=(_completed("deep-research"), _completed("exa")),
                candidate_profile=sample_candidate_profile(),
                baseline_metrics=(("score", 0.50),),
                candidate_metrics=(("score", 0.60),),
                contract_fingerprints=(("ATHENA", "athena-v1"),),
                current_contract_fingerprints=(("ATHENA", "athena-v1"), ("ATHENA", "athena-v2")),
            )
        )
