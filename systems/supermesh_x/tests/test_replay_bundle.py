from scripts.replay_bundle import build_replay_bundle


def test_replay_bundle_is_point_in_time_and_auditable():
    bundle = build_replay_bundle(
        event={'id':'e1','event_time':'2026-09-24T14:00:00Z','text':'statement'},
        evidence=[{'id':'s1','available_time':'2026-09-24T14:00:05Z','source_family':'official'}],
        market=[{'asset':'NQ','observed_time':'2026-09-24T14:01:00Z','price':25000}],
        cutoff='2026-09-24T14:01:30Z'
    )
    assert bundle['event']['id'] == 'e1'
    assert bundle['point_in_time'] is True
    assert bundle['bundle_hash']
