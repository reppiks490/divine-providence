from scripts.event_dedup import canonical_event_key, cluster_events


def test_canonical_event_key_ignores_source_syndication():
    a = {'entity':'Donald Trump','text':'Tariffs on steel increase to 25%','published_time':'2026-09-24T14:00:05Z','source_family':'truth_social'}
    b = {'entity':'donald trump','text':'Tariffs on steel increase to 25%!','published_time':'2026-09-24T14:00:40Z','source_family':'news_wire'}
    assert canonical_event_key(a, bucket_seconds=120) == canonical_event_key(b, bucket_seconds=120)


def test_cluster_events_keeps_independent_source_families():
    events = [
        {'id':'a','entity':'Elon Musk','text':'Example announcement','published_time':'2026-09-24T14:00:00Z','source_family':'x'},
        {'id':'b','entity':'Elon Musk','text':'Example announcement','published_time':'2026-09-24T14:00:50Z','source_family':'news_wire'},
    ]
    clusters = cluster_events(events, bucket_seconds=120)
    assert len(clusters) == 1
    assert clusters[0]['independent_source_families'] == 2
    assert clusters[0]['event_ids'] == ['a','b']
