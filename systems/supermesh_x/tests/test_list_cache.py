from scripts.list_cache import normalize_list_cache, cache_is_fresh, subscription_policy


def test_modern_missing_cache_fields_fail_conservative():
    n=normalize_list_cache({}, protocol_version='2026-07-28', observed_at_ms=1000)
    assert n['ttl_ms']==0 and n['cache_scope']=='private' and n['fresh_until_ms']==1000


def test_public_cache_ttl_is_bounded_and_fresh():
    n=normalize_list_cache({'ttlMs':5000,'cacheScope':'public'}, protocol_version='2026-07-28', observed_at_ms=1000, max_ttl_ms=3000)
    assert n['ttl_ms']==3000 and n['cache_scope']=='public'
    assert cache_is_fresh(n, now_ms=3999) is True
    assert cache_is_fresh(n, now_ms=4000) is False


def test_private_cache_never_crosses_principal():
    n=normalize_list_cache({'ttlMs':5000,'cacheScope':'private'}, protocol_version='2026-07-28', observed_at_ms=0, principal='alice')
    assert cache_is_fresh(n, now_ms=1, principal='bob') is False
    assert cache_is_fresh(n, now_ms=1, principal='alice') is True


def test_legacy_list_change_uses_legacy_notifications():
    p=subscription_policy('2025-11-25', {'tools':True,'prompts':False,'resources':True})
    assert p['transport']=='legacy_unsolicited'
    assert p['listen_filter'] is None


def test_modern_list_change_requires_listen_and_intersects_capabilities():
    p=subscription_policy('2026-07-28', {'tools':True,'prompts':True,'resources':False}, advertised={'tools':True,'prompts':False,'resources':True})
    assert p['transport']=='subscriptions/listen'
    assert p['listen_filter']=={'tools':True,'prompts':False,'resources':False}
