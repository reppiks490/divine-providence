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
