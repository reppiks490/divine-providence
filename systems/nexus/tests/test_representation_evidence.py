from nexus.representation_evidence import (
    build_representation_source_evidence,
    tradingview_timeframe_seconds,
)


def test_tradingview_timeframe_parser_uses_reviewed_syntax():
    assert tradingview_timeframe_seconds("1S") == 1
    assert tradingview_timeframe_seconds("10S") == 10
    assert tradingview_timeframe_seconds("30S") == 30
    assert tradingview_timeframe_seconds("1") == 60
    assert tradingview_timeframe_seconds("240") == 14_400
    assert tradingview_timeframe_seconds("60") == 3_600
    assert tradingview_timeframe_seconds("1H") is None
    assert tradingview_timeframe_seconds("2S") is None


def test_source_evidence_separates_cadence_compatibility_without_resolution():
    triage = {
        "clusters": [
            {
                "triage_class": "FIXED_TIME_CADENCE_MATCH_REQUIRES_EXPORT_PROVENANCE",
                "venue": "CME",
                "symbols": ["NQ1!"],
                "stream_ids": ["a", "b"],
                "stream_count": 2,
                "filename_claim": "1S",
                "observed_cadence_ns": 1_000_000_000,
            },
            {
                "triage_class": "EVENT_OR_TRANSFORMED_REQUIRES_VENDOR_DEFINITION",
                "venue": "CME",
                "symbols": ["NQ1!"],
                "stream_ids": ["c"],
                "stream_count": 1,
                "filename_claim": "1",
                "observed_cadence_ns": 1_000_000,
            },
        ]
    }
    out = build_representation_source_evidence(triage)
    assert out["p0_stream_count"] == 3
    assert out["standard_timeframe_cadence_compatible_stream_count"] == 2
    assert out["standard_timeframe_cadence_incompatible_stream_count"] == 1
    assert out["auto_resolved_count"] == 0
    assert out["production_authorized"] is False
    exact = next(x for x in out["clusters"] if x["stream_ids"] == ["a", "b"])
    assert exact["claim_vs_observed"] == "EXACT_CADENCE_MATCH"
    assert exact["remaining_p0"] is True
    mismatch = next(x for x in out["clusters"] if x["stream_ids"] == ["c"])
    assert mismatch["claim_vs_observed"] == "OBSERVED_FASTER_THAN_STANDARD_TIMEFRAME_CLAIM"
    assert mismatch["source_evidence"]["chart_type_standard_time_based"] == "NOT_ATTESTED"
