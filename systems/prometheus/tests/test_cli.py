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
    assert len(payload["external_attestation_ids"]) == 2
    assert len(payload["attestation_verification_ids"]) == 2
    assert payload["attestation_coverage_gaps"] == []
    assert payload["provenance_manifest_id"].startswith("research-provenance:")
    assert payload["provenance_lineage_report_id"].startswith("provenance-lineage:")
    assert payload["promotion_packet_id"].startswith("promotion-packet:")
    assert payload["cryptographic_verification_performed_by_prometheus"] is False
    assert payload["production_authorized"] is False
