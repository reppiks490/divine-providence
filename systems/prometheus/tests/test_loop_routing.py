from prometheus_loop.contracts import (
    CandidateImprovement,
    DeferredExperiment,
    ExperimentRouteAction,
    LoopKind,
    ObservationEnvelope,
)
from prometheus_loop.fixtures import sample_candidate_profile, sample_observations, sample_plugins
from prometheus_loop.memory.store import ResearchMemory
from prometheus_loop.orchestration.loop import HostPluginResult, PrometheusLoop, RunInput


def _completed(plugin_id: str):
    return HostPluginResult(
        plugin_id=plugin_id,
        success=True,
        input_fingerprint=f"input:{plugin_id}",
        output_fingerprint=f"output:{plugin_id}",
    )


def _base(observations, **overrides):
    values = dict(
        run_kind=LoopKind.FORGE,
        objective="research architecture validation with source-backed analysis",
        observations=observations,
        plugin_inventory=sample_plugins(),
        plugin_results=(_completed("deep-research"), _completed("exa")),
        candidate_profile=sample_candidate_profile(),
        baseline_metrics=(("score", 0.50),),
        candidate_metrics=(("score", 0.60),),
    )
    values.update(overrides)
    return RunInput(**values)


def test_loop_chooses_actionable_case_instead_of_first_role_specialization(tmp_path):
    instant = "160"
    observations = (
        ObservationEnvelope(
            sibling="ARGUS",
            decision_instant=instant,
            availability_state="KNOWN",
            evidence_tier="CANDLE_PROXY",
            dimensions=(("contract", "ARGUS"), ("factor:tech", "0.2")),
            source_ref="argus:fixture",
        ),
        ObservationEnvelope(
            sibling="ATHENA",
            decision_instant=instant,
            availability_state="KNOWN",
            evidence_tier="SUPERVISORY",
            dimensions=(("contract", "ATHENA"), ("factor:tech", "0.8")),
            source_ref="athena:fixture",
        ),
    )
    run = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl")).run(_base(observations))
    assert run.route.action is ExperimentRouteAction.RUN_REPLAY
    assert run.route.reason_code == "REDUCIBLE_EVIDENCE_MISMATCH"
    assert run.route.case_id == next(case.artifact_id for case in run.disagreements if case.dimension == "factor:tech")
    assert isinstance(run.result, CandidateImprovement)


def test_stale_preflight_lineage_blocks_replay_before_adversarial_execution(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    run = PrometheusLoop(memory).run(
        _base(
            sample_observations(),
            contract_fingerprints=(("ATHENA", "athena-v1"),),
            current_contract_fingerprints=(("ATHENA", "athena-v2"),),
        )
    )
    assert run.route.action is ExperimentRouteAction.DEFER_FRESH_EVIDENCE
    assert isinstance(run.result, DeferredExperiment)
    assert run.experiment is None
    assert run.hypothesis is None
    assert run.promotion_packet is None
    artifact_types = [line.split('"artifact_type":"', 1)[1].split('"', 1)[0] for line in memory.path.read_text().splitlines() if '"artifact_type"' in line]
    assert "AdversarialReport" not in artifact_types
    assert "ReplayResult" not in artifact_types


def test_specialization_only_disagreement_abstains_without_replay(tmp_path):
    instant = "160"
    observations = (
        ObservationEnvelope(
            sibling="ARGUS",
            decision_instant=instant,
            availability_state="KNOWN",
            evidence_tier="CANDLE_PROXY",
            dimensions=(("contract", "ARGUS"),),
            source_ref="argus:fixture",
        ),
        ObservationEnvelope(
            sibling="ATHENA",
            decision_instant=instant,
            availability_state="KNOWN",
            evidence_tier="SUPERVISORY",
            dimensions=(("contract", "ATHENA"),),
            source_ref="athena:fixture",
        ),
    )
    run = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl")).run(_base(observations))
    assert run.route.action is ExperimentRouteAction.ABSTAIN_SPECIALIZATION
    assert isinstance(run.result, DeferredExperiment)
    assert run.experiment is None
    assert run.promotion_packet is None


def test_negative_reuse_is_scoped_to_preflight_lineage(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    loop = PrometheusLoop(memory)
    bad = sample_candidate_profile(missingness_safe=False)
    first = loop.run(
        _base(
            sample_observations(),
            candidate_profile=bad,
            candidate_metrics=(("score", 0.90),),
            contract_fingerprints=(("ATHENA", "athena-v1"),),
        )
    )
    second = loop.run(
        _base(
            sample_observations(),
            candidate_profile=bad,
            candidate_metrics=(("score", 0.90),),
            contract_fingerprints=(("ATHENA", "athena-v2"),),
        )
    )
    assert first.experiment is not None
    assert second.experiment is not None
    assert first.experiment.artifact_id != second.experiment.artifact_id
    assert second.reused_negative is False
