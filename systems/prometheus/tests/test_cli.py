import json

from prometheus_loop.cli import main


def test_demo_cli_emits_research_only_json(tmp_path, capsys):
    exit_code = main(["demo", "--memory", str(tmp_path / "demo-memory.jsonl")])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["loop_run_id"].startswith("loop:")
    assert payload["status"] == "RESEARCH_COMPLETE"
    assert payload["plugin_audit"]["deep-research"] == "COMPLETED"
    assert payload["plugin_audit"]["exa"] == "COMPLETED"
    assert payload["plugin_audit"]["gmail"] == "SKIPPED_NOT_BENEFICIAL"
    assert payload["disagreement_ids"]
    assert payload["route"]["action"] == "RUN_REPLAY"
    assert payload["route"]["priority_band"] == "MEDIUM"
    assert payload["route"]["reason_code"] == "AMBIGUITY_REDUCTION_PROBE"
    assert payload["result"]["artifact_id"]
    assert payload["result"]["status"] == "PROMETHEUS_ENGINEERING_PASS"
    assert payload.get("production_authorized") is not True


def test_strict_attested_demo_exposes_verified_binding_without_crypto_claim(tmp_path, capsys):
    exit_code = main(["demo-strict-attested", "--memory", str(tmp_path / "strict-memory.jsonl")])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "RESEARCH_COMPLETE"
    assert payload["plugin_attestation_policy"] == "REQUIRE_VERIFIED"
    assert len(payload["plugin_evidence_ids"]) == 2
    assert len(payload["external_attestation_ids"]) == 2
    assert len(payload["attestation_verification_ids"]) == 2
    assert payload["attestation_coverage_gaps"] == []
    assert payload["provenance_manifest_id"].startswith("research-provenance:")
    assert payload["provenance_lineage_report_id"].startswith("provenance-lineage:")
    assert payload["promotion_packet_id"].startswith("promotion-packet:")
    assert payload["cryptographic_verification_performed_by_prometheus"] is False
    assert payload["production_authorized"] is False


def test_export_ascension_handoff_cli_uses_existing_runtime_memory(tmp_path, capsys):
    memory = tmp_path / "strict-memory.jsonl"
    assert main(["demo-strict-attested", "--memory", str(memory)]) == 0
    demo = json.loads(capsys.readouterr().out)

    output = tmp_path / "handoffs" / "prometheus-ascension.json"
    assert main([
        "export-ascension-handoff",
        "--memory", str(memory),
        "--provenance-manifest-id", demo["provenance_manifest_id"],
        "--plugin-evidence-id", demo["plugin_evidence_ids"][0],
        "--output", str(output),
    ]) == 0

    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(output.read_text(encoding="utf-8"))
    assert stdout_payload == file_payload
    assert stdout_payload["sibling_id"] == "PROMETHEUS"
    assert stdout_payload["artifact"]["content_b64"]
    assert stdout_payload["authority"]["attestation"]["plugin_evidence_id"] == demo["plugin_evidence_ids"][0]
    assert stdout_payload["extensions"]["prometheus"]["provenance_manifest_id"] == demo["provenance_manifest_id"]
    assert stdout_payload["extensions"]["prometheus"]["authenticated"] is False
    assert stdout_payload["extensions"]["prometheus"]["transfer_verified"] is False
    assert stdout_payload["extensions"]["prometheus"]["production_authorized"] is False
    assert "adapter_v0_4_evidence" not in stdout_payload
