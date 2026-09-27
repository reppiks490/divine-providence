from scripts.event_fabric import process_event_batch


def test_event_fabric_dedupes_ledgers_and_builds_replayable_shock_summary():
    events=[
        {'id':'p1','entity':'Donald Trump','text':'Public tariff announcement','published_time':'2026-09-24T14:00:00Z','retrieved_time':'2026-09-24T14:00:05Z','source_family':'official','source':'official'},
        {'id':'p2','entity':'donald trump','text':'Public tariff announcement!','published_time':'2026-09-24T14:00:40Z','retrieved_time':'2026-09-24T14:00:50Z','source_family':'news_wire','source':'wire'},
    ]
    reactions={
        'NQ': {'return_z':-2.0,'lag_seconds':60,'channel':'equities'},
        'VIX': {'return_z':2.5,'lag_seconds':30,'channel':'volatility'},
    }
    result=process_event_batch(
        events=events,
        reactions=reactions,
        cutoff='2026-09-24T14:02:00Z',
        evidence=[{'id':'e1','available_time':'2026-09-24T14:00:05Z','source_family':'official'}],
        market=[{'asset':'NQ','observed_time':'2026-09-24T14:01:00Z','price':25000}],
        priority_inputs={'asset_relevance':1,'topic_relevance':1,'recency':1,'historical_impact':0.5,'source_coverage':1},
        base_confidence=0.9,
        age_minutes=2,
        conflict_strength=0.1,
    )
    assert result['cluster_count'] == 1
    assert result['clusters'][0]['independent_source_families'] == 2
    assert result['ledger_verification']['valid'] is True
    assert result['shock_graph']['breadth'] == 2
    assert result['replay']['point_in_time'] is True
    assert result['priority']['policy'] == 'market_relevance_only'
    assert result['confidence']['confidence'] > 0
