import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from recency_weight import recency_score, freshness_bucket


def test_newer_public_event_scores_higher_than_old_event():
    now = '2026-09-24T19:45:00Z'
    newest = recency_score('2026-09-24T19:40:00Z', now)
    older = recency_score('2026-09-17T19:45:00Z', now)
    historical = recency_score('2020-09-24T19:45:00Z', now)
    assert newest > older > historical
    assert freshness_bucket('2026-09-24T19:40:00Z', now) == 'breaking'


def test_future_timestamp_is_rejected():
    now = '2026-09-24T19:45:00Z'
    try:
        recency_score('2026-09-24T20:45:00Z', now)
    except ValueError as exc:
        assert 'future' in str(exc).lower()
    else:
        raise AssertionError('future event must be rejected')
