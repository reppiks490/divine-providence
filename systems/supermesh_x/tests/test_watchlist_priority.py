from scripts.watchlist_priority import score_mover


def test_watchlist_priority_uses_relevance_recency_and_history_without_political_judgment():
    row = score_mover(asset_relevance=1.0, topic_relevance=0.8, recency=0.9, historical_impact=0.7, source_coverage=0.8)
    assert 0 <= row['score'] <= 1
    assert row['score'] > 0.7
    assert row['policy'] == 'market_relevance_only'
