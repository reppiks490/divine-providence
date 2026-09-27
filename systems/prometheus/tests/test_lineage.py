import hashlib
import json

from prometheus_loop.attestation import PluginAttestationPolicy
from prometheus_loop.contracts import CandidateImprovement, ResearchLineageManifest
from prometheus_loop.ids import canonical_json
from prometheus_loop.lineage import build_lineage_manifest, detect_stale_lineage
from prometheus_loop.memory.store import ResearchMemory
from prometheus_loop.provenance import build_research_provenance_manifest
from prometheus_loop.provenance_lineage import verify_provenance_lineage


# --- stale-aware research lineage (prometheus_loop.lineage) ---


def test_lineage_identity_is_deterministic_and_inputs_are_canonicalized():
    first = build_lineage_manifest(
        root_artifact_id="candidate:c",
        artifact_ids=("obs:b", "obs:a", "obs:a"),
        predecessor_ids=("exp:z", "hyp:y", "hyp:y"),
        contract_fingerprints=(("NEXUS", "hash-n"), ("plugin:exa", "hash-e")),
    )
    second = build_lineage_manifest(
        root_artifact_id="candidate:c",
        artifact_ids=("obs:a", "obs:b"),
        predecessor_ids=("hyp:y", "exp:z"),
        contract_fingerprints=(("plugin:exa", "hash-e"), ("NEXUS", "hash-n")),
    )
    assert isinstance(first, ResearchLineageManifest)
    assert first.artifact_ids == ("obs:a", "obs:b")
    assert first.predecessor_ids == ("exp:z", "hyp:y")
    assert first.contract_fingerprints == (("NEXUS", "hash-n"), ("plugin:exa", "hash-e"))
    assert first.artifact_id == second.artifact_id


def test_stale_detection_does_not_mutate_original_lineage():
    lineage = build_lineage_manifest(
        root_artifact_id="candidate:c",
        artifact_ids=("obs:a",),
        predecessor_ids=("hyp:y",),
        contract_fingerprints=(("NEXUS", "hash-old"),),
    )
    original_id = lineage.artifact_id
    report = detect_stale_lineage(lineage, {"NEXUS": "hash-new"})
    assert lineage.artifact_id == original_id
    assert report.lineage_manifest_id == original_id
    assert report.is_stale is True
    assert report.contract_mismatches == (("NEXUS", "hash-old", "hash-new"),)


def test_missing_current_contract_fingerprint_marks_lineage_stale():
    lineage = build_lineage_manifest(
        root_artifact_id="candidate:c",
        artifact_ids=("obs:a",),
        predecessor_ids=(),
        contract_fingerprints=(("NEXUS", "hash-n"), ("plugin:exa", "hash-e")),
    )
    report = detect_stale_lineage(lineage, {"NEXUS": "hash-n"})
    assert report.is_stale is True
    assert report.contract_mismatches == (("plugin:exa", "hash-e", "<MISSING>"),)


def test_extra_current_contracts_do_not_make_prior_lineage_stale():
    lineage = build_lineage_manifest(
        root_artifact_id="candidate:c",
        artifact_ids=("obs:a",),
        predecessor_ids=(),
        contract_fingerprints=(("NEXUS", "hash-n"),),
    )
    report = detect_stale_lineage(lineage, {"NEXUS": "hash-n", "ATHENA": "new"})
    assert report.is_stale is False
    assert report.contract_mismatches == ()


def test_duplicate_contract_names_are_rejected():
    try:
        build_lineage_manifest(
            root_artifact_id="candidate:c",
            artifact_ids=("obs:a",),
            predecessor_ids=(),
            contract_fingerprints=(("NEXUS", "one"), ("NEXUS", "two")),
        )
    except ValueError as exc:
        assert "duplicate contract fingerprint" in str(exc)
    else:
        raise AssertionError("expected conflicting duplicate contract names to fail closed")


# --- provenance-ancestry lineage (prometheus_loop.provenance_lineage) ---


def manifest(*, token, parents=()):
    return build_research_provenance_manifest(
        loop_run_id=f"loop:{token}",
        experiment_id=f"experiment:{token}",
        candidate_id=f"candidate:{token}",
        selected_plugin_descriptor_ids=(),
        plugin_evidence_ids=(),
        plugin_contribution_ids=(),
        observation_ids=(f"observation:{token}",),
        parent_manifest_ids=parents,
        plugin_attestation_policy=PluginAttestationPolicy.OPTIONAL,
    )


def test_root_manifest_has_complete_deterministic_lineage(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    root = manifest(token="root")
    memory.append(root)
    report = verify_provenance_lineage(memory, root.artifact_id)
    assert report.complete is True
    assert report.tip_manifest_id == root.artifact_id
    assert report.verified_manifest_ids == (root.artifact_id,)
    assert report.root_manifest_ids == (root.artifact_id,)
    assert report.edge_ids == ()
    assert report.failure_reasons == ()
    assert report.artifact_id.startswith("provenance-lineage:")


def test_multi_generation_and_convergent_dag_are_verified_once_with_sorted_edges(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    root = manifest(token="root")
    left = manifest(token="left", parents=(root.artifact_id,))
    right = manifest(token="right", parents=(root.artifact_id,))
    tip = manifest(token="tip", parents=(right.artifact_id, left.artifact_id))
    for item in (root, left, right, tip):
        memory.append(item)

    report = verify_provenance_lineage(memory, tip.artifact_id)
    assert report.complete is True
    assert report.verified_manifest_ids == tuple(sorted({root.artifact_id, left.artifact_id, right.artifact_id, tip.artifact_id}))
    assert report.root_manifest_ids == (root.artifact_id,)
    assert report.edge_ids == tuple(sorted((
        f"{root.artifact_id} -> {left.artifact_id}",
        f"{root.artifact_id} -> {right.artifact_id}",
        f"{left.artifact_id} -> {tip.artifact_id}",
        f"{right.artifact_id} -> {tip.artifact_id}",
    )))


def test_missing_parent_is_incomplete_not_inferred_as_root(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    tip = manifest(token="tip", parents=("research-provenance:" + "f" * 64,))
    memory.append(tip)
    report = verify_provenance_lineage(memory, tip.artifact_id)
    assert report.complete is False
    assert any("missing parent manifest" in reason for reason in report.failure_reasons)
    assert report.root_manifest_ids == ()


def test_wrong_type_parent_is_rejected(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    wrong = CandidateImprovement(
        experiment_id="experiment:wrong",
        status=__import__("prometheus_loop.contracts", fromlist=["CandidateStatus"]).CandidateStatus.RESEARCH_ONLY,
        evidence_ids=("evidence:1",),
        summary="wrong type",
    )
    memory.append(wrong)
    tip = manifest(token="tip", parents=(wrong.artifact_id.replace("candidate:", "research-provenance:"),))
    memory.append(tip)
    # rewrite candidate record id so lookup resolves under a provenance-shaped id while type stays wrong
    record = memory.find_by_id(wrong.artifact_id).copy()
    fake_id = tip.parent_manifest_ids[0]
    record["artifact_id"] = fake_id
    path = memory.path
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    lines[0] = record
    path.write_text("\n".join(canonical_json(line) for line in lines) + "\n")
    reloaded = ResearchMemory(path)
    report = verify_provenance_lineage(reloaded, tip.artifact_id)
    assert report.complete is False
    assert any("wrong artifact type" in reason for reason in report.failure_reasons)


def test_parent_content_id_mismatch_detected_even_when_memory_checksum_is_recomputed(tmp_path):
    path = tmp_path / "memory.jsonl"
    memory = ResearchMemory(path)
    root = manifest(token="root")
    tip = manifest(token="tip", parents=(root.artifact_id,))
    memory.append(root)
    memory.append(tip)

    records = [json.loads(line) for line in path.read_text().splitlines()]
    records[0]["payload"]["candidate_id"] = "candidate:tampered"
    records[0]["content_sha256"] = hashlib.sha256(canonical_json(records[0]["payload"]).encode()).hexdigest()
    path.write_text("\n".join(canonical_json(record) for record in records) + "\n")

    reloaded = ResearchMemory(path)
    report = verify_provenance_lineage(reloaded, tip.artifact_id)
    assert report.complete is False
    assert any("content id mismatch" in reason for reason in report.failure_reasons)


def _record(artifact_id, payload):
    return {
        "artifact_id": artifact_id,
        "artifact_type": "ResearchProvenanceManifest",
        "payload": payload,
        "content_sha256": hashlib.sha256(canonical_json(payload).encode()).hexdigest(),
    }


def test_cycle_is_detected_fail_closed_even_in_malicious_stored_records(tmp_path):
    path = tmp_path / "memory.jsonl"
    a_id = "research-provenance:" + "a" * 64
    b_id = "research-provenance:" + "b" * 64
    base = dict(
        experiment_id="experiment:x",
        candidate_id="candidate:x",
        selected_plugin_descriptor_ids=[],
        plugin_evidence_ids=[],
        plugin_contribution_ids=[],
        observation_ids=["observation:x"],
        source_contract_ids=[],
        external_attestation_ids=[],
        attestation_verification_ids=[],
        plugin_attestation_policy="OPTIONAL",
    )
    a_payload = dict(base, loop_run_id="loop:a", parent_manifest_ids=[b_id])
    b_payload = dict(base, loop_run_id="loop:b", parent_manifest_ids=[a_id])
    path.write_text(canonical_json(_record(a_id, a_payload)) + "\n" + canonical_json(_record(b_id, b_payload)) + "\n")
    memory = ResearchMemory(path)
    report = verify_provenance_lineage(memory, a_id)
    assert report.complete is False
    assert any("cycle" in reason for reason in report.failure_reasons)


def test_duplicate_parent_ids_in_malicious_record_fail_closed(tmp_path):
    path = tmp_path / "memory.jsonl"
    root = manifest(token="root")
    memory = ResearchMemory(path)
    memory.append(root)
    tip_id = "research-provenance:" + "d" * 64
    payload = dict(
        loop_run_id="loop:tip",
        experiment_id="experiment:tip",
        candidate_id="candidate:tip",
        selected_plugin_descriptor_ids=[],
        plugin_evidence_ids=[],
        plugin_contribution_ids=[],
        observation_ids=["observation:tip"],
        source_contract_ids=[],
        parent_manifest_ids=[root.artifact_id, root.artifact_id],
        external_attestation_ids=[],
        attestation_verification_ids=[],
        plugin_attestation_policy="OPTIONAL",
    )
    with path.open("a") as handle:
        handle.write(canonical_json(_record(tip_id, payload)) + "\n")
    reloaded = ResearchMemory(path)
    report = verify_provenance_lineage(reloaded, tip_id)
    assert report.complete is False
    assert any("duplicate parent" in reason for reason in report.failure_reasons)
