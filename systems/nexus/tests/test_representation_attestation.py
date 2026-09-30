from nexus.contracts import StreamIdentity, StreamManifest
from nexus.representation_attestation import (
    INPUT_SCHEMA,
    build_representation_attestation_status,
)


def _manifest(*, volume=True):
    ident = StreamIdentity("src", "CME", "NQ1!", "1", source_path="archive.zip::NQ.csv", raw_sha256="a" * 64)
    cols = ["time", "open", "high", "low", "close"] + (["volume"] if volume else [])
    return StreamManifest(ident, 10, cols, 1, 10, 60_000_000_000, 1.0, 0, 0, 0)


def _queue(m):
    return {
        "candidates": [{
            "stream_id": m.identity.stream_id,
            "source_path": m.identity.source_path,
            "priority": "P0",
        }]
    }


def _valid(m):
    return {
        "schema": INPUT_SCHEMA,
        "attestations": [{
            "stream_id": m.identity.stream_id,
            "raw_sha256": m.identity.raw_sha256,
            "source_path": m.identity.source_path,
            "reviewed": True,
            "reviewed_by": "human-review",
            "reviewed_at": "2026-09-25",
            "evidence_sources": ["vendor-export-settings:screenshot-sha"],
            "evidence_sha256": "b" * 64,
            "dimensions": {
                "source_vendor": "TradingView",
                "vendor_symbol": "CME_MINI:NQ1!",
                "chart_type": "standard_time_based",
                "timeframe_or_event_definition": "1 minute",
                "timestamp_semantics": "BAR_OPEN",
                "timezone": "America/Chicago",
                "session_definition": "reviewed exchange session",
                "volume_semantics": "trade volume",
            },
        }],
    }


def test_missing_attestation_stays_p0():
    m = _manifest()
    out = build_representation_attestation_status([m], _queue(m), None)
    assert out["resolved_by_attestation_count"] == 0
    assert out["remaining_p0_count"] == 1
    assert out["status_counts"] == {"WAITING_EXPORT_SPECIFIC_ATTESTATION": 1}
    assert out["production_authorized"] is False


def test_exact_stream_attestation_can_discharge_representation_definition_only():
    m = _manifest()
    out = build_representation_attestation_status([m], _queue(m), _valid(m))
    assert out["resolved_by_attestation_count"] == 1
    assert out["remaining_p0_count"] == 0
    assert out["status_counts"] == {"RESOLVED_BY_EXACT_STREAM_ATTESTATION": 1}
    assert out["production_authorized"] is False


def test_attestation_cannot_be_inherited_across_different_bytes():
    m = _manifest()
    payload = _valid(m)
    payload["attestations"][0]["raw_sha256"] = "c" * 64
    out = build_representation_attestation_status([m], _queue(m), payload)
    assert out["resolved_by_attestation_count"] == 0
    assert out["status_counts"] == {"REJECTED_ATTESTATION_IDENTITY_MISMATCH": 1}


def test_volume_dimension_only_required_when_volume_present():
    m = _manifest(volume=False)
    payload = _valid(m)
    payload["attestations"][0]["dimensions"].pop("volume_semantics")
    out = build_representation_attestation_status([m], _queue(m), payload)
    assert out["resolved_by_attestation_count"] == 1


def test_review_and_source_evidence_are_mandatory():
    m = _manifest()
    payload = _valid(m)
    payload["attestations"][0]["reviewed"] = False
    payload["attestations"][0]["evidence_sources"] = []
    out = build_representation_attestation_status([m], _queue(m), payload)
    assert out["resolved_by_attestation_count"] == 0
    assert out["status_counts"] == {"BLOCKED_ATTESTATION_EVIDENCE_INCOMPLETE": 1}


def test_attestation_requires_reviewer_time_and_valid_timestamp_semantics():
    m=_manifest()
    payload=_valid(m)
    payload["attestations"][0]["reviewed_by"]=""
    payload["attestations"][0]["reviewed_at"]="not-a-date"
    out=build_representation_attestation_status([m],_queue(m),payload)
    assert out["resolved_by_attestation_count"]==0
    assert out["status_counts"]=={"BLOCKED_ATTESTATION_EVIDENCE_INCOMPLETE":1}

    payload=_valid(m)
    payload["attestations"][0]["dimensions"]["timestamp_semantics"]="BANANA"
    out=build_representation_attestation_status([m],_queue(m),payload)
    assert out["resolved_by_attestation_count"]==0
    assert out["status_counts"]=={"BLOCKED_ATTESTATION_DIMENSIONS_INCOMPLETE":1}


def test_exact_byte_alias_path_is_valid_attestation_identity():
    m=_manifest()
    alias=_manifest()
    alias.identity=StreamIdentity(
        alias.identity.source_id,alias.identity.venue,alias.identity.symbol,
        alias.identity.filename_claim,alias.identity.representation,
        "archive.zip::copy/NQ.csv",alias.identity.raw_sha256,
    )
    payload=_valid(m)
    payload["attestations"][0]["source_path"]=alias.identity.source_path
    out=build_representation_attestation_status([alias,m],_queue(m),payload)
    assert out["resolved_by_attestation_count"]==1
    assert out["remaining_p0_count"]==0


def test_contradictory_valid_attestations_fail_closed():
    m=_manifest()
    payload=_valid(m)
    second=dict(payload["attestations"][0])
    second["dimensions"]=dict(second["dimensions"])
    second["dimensions"]["chart_type"]="heikin_ashi"
    second["reviewed_by"]="second-reviewer"
    second["reviewed_at"]="2026-09-26"
    payload["attestations"].append(second)
    out=build_representation_attestation_status([m],_queue(m),payload)
    assert out["resolved_by_attestation_count"]==0
    assert out["remaining_p0_count"]==1
    assert out["status_counts"]=={"BLOCKED_ATTESTATION_CONFLICT":1}
    assert out["streams"][0]["valid_attestation_count"]==2


def test_multiple_valid_attestations_must_agree_but_can_merge_evidence_sources():
    m=_manifest()
    payload=_valid(m)
    second={
        **payload["attestations"][0],
        "reviewed_by":"second-reviewer",
        "reviewed_at":"2026-09-26",
        "evidence_sources":["vendor-contract:sha"],
    }
    second["dimensions"]=dict(payload["attestations"][0]["dimensions"])
    payload["attestations"].append(second)
    out=build_representation_attestation_status([m],_queue(m),payload)
    assert out["resolved_by_attestation_count"]==1
    row=out["streams"][0]
    assert row["valid_attestation_count"]==2
    assert row["accepted_dimensions"]["timestamp_semantics"]=="BAR_OPEN"
    assert set(row["accepted_evidence_sources"])=={
        "vendor-export-settings:screenshot-sha","vendor-contract:sha"
    }
