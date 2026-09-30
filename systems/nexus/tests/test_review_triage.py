from nexus.review_triage import build_representation_review_triage


def test_review_triage_groups_without_auto_resolution():
    q = {"candidates": [
        {
            "priority": "P0", "hypothesis_kind": "event_or_transformed_candidate",
            "venue": "CME", "symbol": "NQ1!", "filename_claim": "1",
            "observed_cadence_ns": 1_000_000, "quality_flags": ["claim_mismatch", "fractional_time"],
            "review_reasons": ["flag:claim_mismatch"], "evidence_required": ["vendor definition"], "stream_id": "a",
        },
        {
            "priority": "P0", "hypothesis_kind": "event_or_transformed_candidate",
            "venue": "CME", "symbol": "ES1!", "filename_claim": "1",
            "observed_cadence_ns": 1_000_000, "quality_flags": ["claim_mismatch", "fractional_time"],
            "review_reasons": ["flag:claim_mismatch"], "evidence_required": ["vendor definition"], "stream_id": "b",
        },
        {
            "priority": "P0", "hypothesis_kind": "timeframe_mismatch_candidate",
            "venue": "CME", "symbol": "NQ1!", "filename_claim": "2",
            "observed_cadence_ns": 3_600_000_000_000, "quality_flags": ["cadence_ambiguous"],
            "review_reasons": ["hypothesis:timeframe_mismatch_candidate"], "evidence_required": ["export settings"], "stream_id": "c",
        },
        {"priority": "P2", "hypothesis_kind": "fixed_time_candidate", "stream_id": "d"},
    ]}
    out = build_representation_review_triage(q)
    assert out["p0_count"] == 3
    assert out["p2_count"] == 1
    assert out["triage_class_counts"]["EVENT_DRIVEN_REQUIRES_VENDOR_DEFINITION"] == 2
    assert out["triage_class_counts"]["TIMEFRAME_MISMATCH_REQUIRES_EXPORT_SETTING_EVIDENCE"] == 1
    assert out["auto_resolved_count"] == 0
    assert out["production_authorized"] is False
    assert any(c["stream_count"] == 2 for c in out["clusters"])
