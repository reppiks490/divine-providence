import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from public_signal import normalize_signal


def test_normalize_public_social_signal_preserves_times_and_provenance():
    row=normalize_signal({
        'entity':'Donald Trump','platform':'public_social','source':'https://example.test/post/1',
        'published_time':'2026-09-24T15:00:00Z','retrieved_time':'2026-09-24T15:00:05Z',
        'text':'Tariff announcement concerning semiconductors','topics':['trade','semiconductors']
    })
    assert row['entity']=='Donald Trump'
    assert row['signal_type']=='social_post'
    assert row['event_time']=='2026-09-24T15:00:00Z'
    assert row['public_only'] is True
    assert row['content_hash']
    assert row['provenance']['source']=='https://example.test/post/1'


def test_normalize_signal_rejects_private_location_tracking():
    try:
        normalize_signal({'entity':'Person','signal_type':'private_location','source':'x','published_time':'2026-01-01T00:00:00Z'})
    except ValueError as exc:
        assert 'public' in str(exc).lower()
    else:
        raise AssertionError('private location signals must be rejected')
