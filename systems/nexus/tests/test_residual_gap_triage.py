from nexus.contracts import StreamIdentity, StreamManifest
from nexus.residual_gap_triage import classify_residual_gaps


def _m(symbol: str, raw: str, cadence: int, first: int, last: int, rows: int = 1000):
    return StreamManifest(
        identity=StreamIdentity("zipcsv", "CME", symbol, "1", "csv_export", f"{raw}.csv", raw * 64),
        row_count=rows,
        columns=["time", "open", "high", "low", "close"],
        first_event_ns=first,
        last_event_ns=last,
        observed_cadence_ns=cadence,
        cadence_confidence=1.0,
        repeated_timestamp_count=0,
        backward_timestamp_count=0,
        fractional_timestamp_count=0,
        quality_flags=[],
        metadata={"logical_sha256": raw * 64},
    )


def test_cross_resolution_activity_is_diagnostic_not_data_loss_claim():
    target = _m("NQ1!", "a", 10, 0, 1000)
    sibling = _m("NQ1!", "b", 5, 0, 1000)
    gaps = [(100 + i * 20, 120 + i * 20) for i in range(20)]
    times = [a + 5 for a, _ in gaps]
    out = classify_residual_gaps(
        candidate_id="c1", target=target, residual_gaps=gaps,
        sibling_times={sibling.identity.stream_id: times}, siblings=[sibling],
    )
    assert out.classification == "CROSS_RESOLUTION_ACTIVITY_PRESENT_DOMINANT"
    assert out.gaps_with_sibling_activity == 20
    assert out.data_loss_asserted is False
    assert out.production_authorized is False


def test_shared_silence_does_not_claim_no_trades_or_completeness():
    target = _m("ES1!", "c", 10, 0, 1000)
    sibling = _m("ES1!", "d", 5, 0, 1000)
    gaps = [(100 + i * 20, 120 + i * 20) for i in range(20)]
    # Sibling covers the intervals but has observations only at the outer dataset bounds.
    out = classify_residual_gaps(
        candidate_id="c2", target=target, residual_gaps=gaps,
        sibling_times={sibling.identity.stream_id: [0, 1000]}, siblings=[sibling],
    )
    assert out.classification == "SHARED_SILENCE_DOMINANT"
    assert out.gaps_with_shared_silence == 20
    assert out.data_loss_asserted is False


def test_low_cross_resolution_coverage_fails_closed():
    target = _m("YM1!", "e", 10, 0, 1000)
    sibling = _m("YM1!", "f", 5, 0, 150)
    gaps = [(100 + i * 20, 120 + i * 20) for i in range(20)]
    out = classify_residual_gaps(
        candidate_id="c3", target=target, residual_gaps=gaps,
        sibling_times={sibling.identity.stream_id: [0, 105, 125, 145]}, siblings=[sibling],
    )
    assert out.classification == "INSUFFICIENT_TEMPORAL_SIBLING_COVERAGE"
    assert out.evidence_strength == "LIMITED"


def test_sibling_selection_prioritizes_temporal_overlap():
    from nexus.residual_gap_triage import _eligible_siblings
    target = _m("NQ1!", "1", 100, 1_000, 2_000)
    # Five ultra-fine but disjoint siblings should not crowd out an overlapping one.
    disjoint = [_m("NQ1!", str(i + 2), 1, 0, 500) for i in range(5)]
    overlapping = _m("NQ1!", "8", 50, 1_000, 2_000)
    chosen = _eligible_siblings(target, [target, *disjoint, overlapping])
    assert overlapping.identity.stream_id in {m.identity.stream_id for m in chosen}
