from scripts.confidence_decay import decayed_confidence


def test_confidence_decay_penalizes_age_and_unresolved_conflict():
    fresh = decayed_confidence(0.9, age_minutes=5, conflict_strength=0.0)
    stale = decayed_confidence(0.9, age_minutes=240, conflict_strength=0.5)
    assert fresh['confidence'] > stale['confidence']
    assert stale['confidence'] < 0.5
