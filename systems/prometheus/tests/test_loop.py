import pytest

from prometheus_loop.contracts import LoopKind, RejectedHypothesis, RunStatus
from prometheus_loop.fixtures import sample_candidate_profile, sample_observations, sample_plugins
from prometheus_loop.memory.store import ResearchMemory
from prometheus_loop.orchestration.loop import HostPluginResult, PrometheusLoop, RunInput


def completed(plugin_id, output):
    return HostPluginResult(
        plugin_id=plugin_id,
        success=True,
        input_fingerprint=f"input:{plugin_id}",
        output_fingerprint=f"output:{output}",
    )


def test_end_to_end_loop_selects_beneficial_plugins_and_emits_research_artifact(tmp_path):
    loop = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl"))
    run = loop.run(
        RunInput(
            run_kind=LoopKind.FORGE,
            objective="research architecture validation with source-backed analysis",
            observations=sample_observations(),
            plugin_inventory=sample_plugins(),
            plugin_results=(completed("deep-research", "dr"), completed("exa", "exa")),
            candidate_profile=sample_candidate_profile(),
            baseline_metrics=(("score", 0.50), ("drawdown", 0.20)),
            candidate_metrics=(("score", 0.62), ("drawdown", 0.18)),
            source_contract_ids=("source-contract:fixture",),
        )
    )
    decisions = {d.plugin_id: d.status.value for d in run.plugin_audit.decisions}
    assert run.status is RunStatus.RESEARCH_COMPLETE
    assert decisions == {
        "deep-research": "SELECTED",
        "exa": "SELECTED",
        "gmail": "SKIPPED_NOT_BENEFICIAL",
    }
    assert len(run.disagreements) >= 1
    assert run.result.artifact_id
    assert run.plugin_audit.use_for("deep-research").status.value == "COMPLETED"
    assert len(run.plugin_evidence_ids) == 2
    assert run.promotion_packet is not None
    assert run.promotion_packet.production_authorized is False
    assert run.provenance_manifest_id is not None
    assert run.promotion_packet.provenance_manifest_id == run.provenance_manifest_id
    manifest_record = loop.memory.find_by_id(run.provenance_manifest_id)
    assert manifest_record["artifact_type"] == "ResearchProvenanceManifest"
    assert manifest_record["payload"]["loop_run_id"] == run.loop_run_id
    assert manifest_record["payload"]["experiment_id"] == run.experiment.artifact_id
    assert manifest_record["payload"]["candidate_id"] == run.result.artifact_id
    assert manifest_record["payload"]["source_contract_ids"] == ["source-contract:fixture"]
    assert manifest_record["payload"]["parent_manifest_ids"] == []


def test_deep_research_unavailable_forces_degraded_status(tmp_path):
    plugins = tuple(
        plugin if plugin.plugin_id != "deep-research" else plugin.__class__(
            plugin_id=plugin.plugin_id,
            display_name=plugin.display_name,
            capabilities=plugin.capabilities,
            benefit_tags=plugin.benefit_tags,
            available=False,
            policy_eligible=plugin.policy_eligible,
            redundancy_group=plugin.redundancy_group,
        )
        for plugin in sample_plugins()
    )
    loop = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl"))
    run = loop.run(
        RunInput(
            run_kind=LoopKind.FORGE,
            objective="research architecture validation with source-backed analysis",
            observations=sample_observations(),
            plugin_inventory=plugins,
            plugin_results=(completed("exa", "exa"),),
            candidate_profile=sample_candidate_profile(),
            baseline_metrics=(("score", 0.50),),
            candidate_metrics=(("score", 0.60),),
        )
    )
    assert run.status is RunStatus.DEGRADED_RESEARCH
    assert run.promotion_packet is None
    assert run.provenance_manifest_id is None


def test_selected_plugin_without_host_execution_record_fails_closed(tmp_path):
    loop = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl"))
    with pytest.raises(ValueError, match="selected plugin.*not executed"):
        loop.run(
            RunInput(
                run_kind=LoopKind.FORGE,
                objective="research architecture validation with source-backed analysis",
                observations=sample_observations(),
                plugin_inventory=sample_plugins(),
                plugin_results=(completed("exa", "exa"),),
                candidate_profile=sample_candidate_profile(),
                baseline_metrics=(("score", 0.50),),
                candidate_metrics=(("score", 0.60),),
            )
        )


def test_negative_experiment_is_reused_on_exact_repeat(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    loop = PrometheusLoop(memory)
    bad = sample_candidate_profile(missingness_safe=False)
    args = RunInput(
        run_kind=LoopKind.FORGE,
        objective="research architecture validation with source-backed analysis",
        observations=sample_observations(),
        plugin_inventory=sample_plugins(),
        plugin_results=(completed("deep-research", "dr"), completed("exa", "exa")),
        candidate_profile=bad,
        baseline_metrics=(("score", 0.50),),
        candidate_metrics=(("score", 0.90),),
    )
    first = loop.run(args)
    second = loop.run(args)
    assert isinstance(first.result, RejectedHypothesis)
    assert second.reused_negative is True
    assert second.result.artifact_id == first.result.artifact_id
    assert second.provenance_manifest_id is None

def test_duplicate_host_plugin_execution_records_fail_closed(tmp_path):
    loop = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl"))
    duplicate_deep = completed("deep-research", "dr-2")
    with pytest.raises(ValueError, match="duplicate host plugin result"):
        loop.run(
            RunInput(
                run_kind=LoopKind.FORGE,
                objective="research architecture validation with source-backed analysis",
                observations=sample_observations(),
                plugin_inventory=sample_plugins(),
                plugin_results=(
                    completed("deep-research", "dr-1"),
                    duplicate_deep,
                    completed("exa", "exa"),
                ),
                candidate_profile=sample_candidate_profile(),
                baseline_metrics=(("score", 0.50),),
                candidate_metrics=(("score", 0.60),),
            )
        )


from prometheus_loop.attestation import (
    AttestationVerificationReceipt,
    ExternalExecutionAttestation,
    PluginAttestationPolicy,
)
from prometheus_loop.ids import content_id
from prometheus_loop.plugins import PluginDecisionStatus, PluginExecutionEvidence


def _expected_loop_id(*, policy, objective, observations, inventory, profile, source_contract_ids=(), parent_manifest_ids=()):
    return content_id(
        "loop",
        {
            "run_kind": LoopKind.FORGE.value,
            "objective": objective,
            "observations": [item.artifact_id for item in observations],
            "plugins": [item.descriptor_id for item in inventory],
            "candidate_fingerprint": content_id("candidate-profile", profile),
            "source_contract_ids": tuple(sorted(source_contract_ids)),
            "parent_manifest_ids": tuple(sorted(parent_manifest_ids)),
            "plugin_attestation_policy": policy.value,
        },
    )


def _attested_completed(plugin_id, token, *, loop_run_id, inventory, verified=True):
    host = completed(plugin_id, token)
    descriptor = next(item for item in inventory if item.plugin_id == plugin_id)
    evidence = PluginExecutionEvidence(
        loop_run_id=loop_run_id,
        plugin_id=plugin_id,
        plugin_descriptor_id=descriptor.descriptor_id,
        status=PluginDecisionStatus.COMPLETED,
        input_fingerprint=host.input_fingerprint,
        output_fingerprint=host.output_fingerprint,
        contributed_artifact_ids=(),
    )
    attestation = ExternalExecutionAttestation(
        plugin_evidence_id=evidence.artifact_id,
        subject_sha256=evidence.artifact_id.split(":", 1)[1],
        predicate_type="https://example.invalid/plugin-execution/v1",
        envelope_ref=f"store://attestation/{plugin_id}",
        envelope_sha256=("a" if plugin_id == "deep-research" else "b") * 64,
        verification_material_sha256=("c" if plugin_id == "deep-research" else "d") * 64,
        signer_identity=f"host://{plugin_id}",
        attestation_format="application/vnd.in-toto+json",
    )
    receipt = AttestationVerificationReceipt(
        attestation_id=attestation.artifact_id,
        verifier_id="verifier://fixture/v1",
        trusted_root_id="trust-root://fixture/v1",
        verification_policy_id="policy://fixture/v1",
        checks=(
            ("signature", verified),
            ("subject_digest", True),
            ("signer_identity", True),
            ("trusted_root", True),
        ),
        external_verification_ref=f"store://verification/{plugin_id}",
    )
    return HostPluginResult(
        plugin_id=host.plugin_id,
        success=host.success,
        input_fingerprint=host.input_fingerprint,
        output_fingerprint=host.output_fingerprint,
        external_attestation=attestation,
        attestation_verification=receipt,
    )


def _attestation_run_input(*, policy, plugin_results=None):
    objective = "research architecture validation with source-backed analysis"
    observations = sample_observations()
    inventory = sample_plugins()
    profile = sample_candidate_profile()
    loop_id = _expected_loop_id(
        policy=policy,
        objective=objective,
        observations=observations,
        inventory=inventory,
        profile=profile,
    )
    if plugin_results is None and policy is PluginAttestationPolicy.REQUIRE_VERIFIED:
        plugin_results = (
            _attested_completed("deep-research", "dr", loop_run_id=loop_id, inventory=inventory),
            _attested_completed("exa", "exa", loop_run_id=loop_id, inventory=inventory),
        )
    elif plugin_results is None:
        plugin_results = (completed("deep-research", "dr"), completed("exa", "exa"))
    return RunInput(
        run_kind=LoopKind.FORGE,
        objective=objective,
        observations=observations,
        plugin_inventory=inventory,
        plugin_results=plugin_results,
        candidate_profile=profile,
        baseline_metrics=(("score", 0.50),),
        candidate_metrics=(("score", 0.60),),
        plugin_attestation_policy=policy,
    )


def test_optional_attestation_policy_allows_absence_and_reports_coverage_gap(tmp_path):
    result = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl")).run(
        _attestation_run_input(policy=PluginAttestationPolicy.OPTIONAL)
    )
    assert result.status is RunStatus.RESEARCH_COMPLETE
    assert result.external_attestation_ids == ()
    assert result.attestation_verification_ids == ()
    assert result.attestation_coverage_gaps == ("deep-research", "exa")
    assert result.provenance_manifest_id is not None


def test_optional_policy_rejects_half_supplied_attestation_pair(tmp_path):
    base = _attestation_run_input(policy=PluginAttestationPolicy.OPTIONAL)
    host = base.plugin_results[0]
    loop_id = _expected_loop_id(
        policy=PluginAttestationPolicy.OPTIONAL,
        objective=base.objective,
        observations=base.observations,
        inventory=base.plugin_inventory,
        profile=base.candidate_profile,
    )
    full = _attested_completed(host.plugin_id, "dr", loop_run_id=loop_id, inventory=base.plugin_inventory)
    malformed = HostPluginResult(
        plugin_id=full.plugin_id,
        success=True,
        input_fingerprint=full.input_fingerprint,
        output_fingerprint=full.output_fingerprint,
        external_attestation=full.external_attestation,
    )
    with pytest.raises(ValueError, match="attestation and verification receipt.*together"):
        PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl")).run(
            RunInput(**{**base.__dict__, "plugin_results": (malformed, base.plugin_results[1])})
        )


def test_strict_attestation_policy_degrades_when_coverage_missing(tmp_path):
    base = _attestation_run_input(policy=PluginAttestationPolicy.REQUIRE_VERIFIED, plugin_results=(completed("deep-research", "dr"), completed("exa", "exa")))
    result = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl")).run(base)
    assert result.status is RunStatus.DEGRADED_RESEARCH
    assert result.attestation_coverage_gaps == ("deep-research", "exa")
    assert result.provenance_manifest_id is None
    assert result.promotion_packet is None


def test_strict_attestation_policy_degrades_when_receipt_is_unverified(tmp_path):
    base = _attestation_run_input(policy=PluginAttestationPolicy.REQUIRE_VERIFIED)
    bad = _attested_completed(
        "exa",
        "exa",
        loop_run_id=base.plugin_results[0].external_attestation.plugin_evidence_id and _expected_loop_id(
            policy=PluginAttestationPolicy.REQUIRE_VERIFIED,
            objective=base.objective,
            observations=base.observations,
            inventory=base.plugin_inventory,
            profile=base.candidate_profile,
        ),
        inventory=base.plugin_inventory,
        verified=False,
    )
    result = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl")).run(
        RunInput(**{**base.__dict__, "plugin_results": (base.plugin_results[0], bad)})
    )
    assert result.status is RunStatus.DEGRADED_RESEARCH
    assert result.provenance_manifest_id is None
    assert result.promotion_packet is None


def test_strict_attestation_policy_accepts_complete_verified_coverage_and_persists_artifacts(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    result = PrometheusLoop(memory).run(_attestation_run_input(policy=PluginAttestationPolicy.REQUIRE_VERIFIED))
    assert result.status is RunStatus.RESEARCH_COMPLETE
    assert len(result.external_attestation_ids) == 2
    assert len(result.attestation_verification_ids) == 2
    assert result.attestation_coverage_gaps == ()
    for artifact_id in (*result.external_attestation_ids, *result.attestation_verification_ids):
        assert memory.find_by_id(artifact_id)
    manifest = memory.find_by_id(result.provenance_manifest_id)["payload"]
    assert manifest["plugin_attestation_policy"] == "REQUIRE_VERIFIED"
    assert len(manifest["external_attestation_ids"]) == 2
    assert len(manifest["attestation_verification_ids"]) == 2


def test_attestation_policy_changes_loop_identity(tmp_path):
    loop = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl"))
    optional = loop.run(_attestation_run_input(policy=PluginAttestationPolicy.OPTIONAL))
    strict_missing = loop.run(_attestation_run_input(
        policy=PluginAttestationPolicy.REQUIRE_VERIFIED,
        plugin_results=(completed("deep-research", "dr"), completed("exa", "exa")),
    ))
    assert optional.loop_run_id != strict_missing.loop_run_id


def test_strict_attestation_policy_degrades_on_partial_selected_plugin_coverage(tmp_path):
    base = _attestation_run_input(policy=PluginAttestationPolicy.REQUIRE_VERIFIED)
    result = PrometheusLoop(ResearchMemory(tmp_path / "memory.jsonl")).run(
        RunInput(**{
            **base.__dict__,
            "plugin_results": (base.plugin_results[0], completed("exa", "exa")),
        })
    )
    assert result.status is RunStatus.DEGRADED_RESEARCH
    assert result.attestation_coverage_gaps == ("exa",)
    assert result.provenance_manifest_id is None
    assert result.promotion_packet is None
