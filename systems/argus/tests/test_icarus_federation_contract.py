from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _contract():
    return json.loads(
        (ROOT / "contracts" / "icarus_federation.v1.json").read_text(
            encoding="utf-8"
        )
    )


def test_icarus_federation_contract_is_receipt_only_and_non_executing():
    contract = _contract()

    assert contract["schema_version"] == "argus-icarus-federation-v1"
    assert contract["producer_repository"] == "reppiks490/divine-providence"
    assert contract["subsystem"] == "argus"
    assert contract["consumer_repository"] == "reppiks490/Icarus"
    assert contract["ingress_mode"] == "immutable-receipt-mirror"
    assert contract["ingress_repository"] == "reppiks490/Icarus"
    assert contract["ingress_path"] == (
        "automation_intelligence/mcp_interface/events"
    )
    assert contract["receipt_schema"] == "icarus-interface-event-v1"
    assert contract["consumer_surface"] == (
        "MCP Evolution and Adaptive Brain observability"
    )
    assert contract["authority_ceiling"] == "RESEARCH"
    assert contract["cross_repository_execution_authorized"] is False
    assert contract["execution_authorized"] is False
    assert contract["production_decision_authorized"] is False
    assert contract["broker_substitution_authorized"] is False


def test_icarus_federation_contract_does_not_pin_or_promote_source_results():
    contract = _contract()

    assert "source_commit" not in contract
    assert "verified" not in contract
    assert "production" not in contract["authority_ceiling"].lower()
    assert all(
        isinstance(note, str) and note.strip()
        for note in contract["notes"]
    )
