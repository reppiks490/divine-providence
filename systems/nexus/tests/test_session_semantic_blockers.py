from nexus.session_semantics import build_session_semantic_blocker_report


def test_blocker_report_separates_coarse_provider_wrapper_and_symbol_identity():
    payload = {
        "resolutions": [
            {"candidate_id": "coarse", "stream_id": "s1", "venue": "CME", "symbol": "ES1!", "profile_status": "EXACT_PROFILE_REVIEWED", "gap_count": 5, "coarse_calendar_gap_count": 5, "session_semantics_resolved": False},
            {"candidate_id": "tvc", "stream_id": "s2", "venue": "TVC", "symbol": "DXY", "profile_status": "NO_REVIEWED_PROFILE", "gap_count": 8, "coarse_calendar_gap_count": 0, "session_semantics_resolved": False},
            {"candidate_id": "lse", "stream_id": "s3", "venue": "LSE", "symbol": "MAG7", "profile_status": "NO_REVIEWED_PROFILE", "gap_count": 9, "coarse_calendar_gap_count": 0, "session_semantics_resolved": False},
            {"candidate_id": "done", "stream_id": "s4", "venue": "CME", "symbol": "NQ1!", "profile_status": "EXACT_PROFILE_REVIEWED", "gap_count": 1, "coarse_calendar_gap_count": 0, "session_semantics_resolved": True},
        ]
    }
    out = build_session_semantic_blocker_report(payload)
    assert out["unresolved_candidate_count"] == 3
    assert out["blocker_class_counts"] == {
        "COARSE_BAR_HOLIDAY_AGGREGATION_SEMANTICS": 1,
        "PROVIDER_WRAPPER_UNDERLYING_SESSION_IDENTITY": 1,
        "SYMBOL_VENUE_CONTRACT_IDENTITY": 1,
    }
    assert all(row["production_authorized"] is False for row in out["blockers"])
