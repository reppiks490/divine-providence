import pytest
from scripts.subscription_guard import SubscriptionGuard


def test_requires_ack_before_delivery():
    g=SubscriptionGuard(debounce_ms=100)
    with pytest.raises(ValueError, match='acknowledgment'):
        g.ingest({'subscription_id':'s1','type':'tools','event_id':'e1','observed_at_ms':1000})


def test_deduplicates_same_event_id():
    g=SubscriptionGuard(debounce_ms=100)
    g.acknowledge('s1', {'tools':True})
    assert g.ingest({'subscription_id':'s1','type':'tools','event_id':'e1','observed_at_ms':1000})['accepted'] is True
    assert g.ingest({'subscription_id':'s1','type':'tools','event_id':'e1','observed_at_ms':1010})['reason']=='duplicate'


def test_debounces_repeated_list_change_and_emits_receipt():
    g=SubscriptionGuard(debounce_ms=100)
    g.acknowledge('s1', {'tools':True})
    first=g.ingest({'subscription_id':'s1','type':'tools','event_id':'e1','observed_at_ms':1000})
    second=g.ingest({'subscription_id':'s1','type':'tools','event_id':'e2','observed_at_ms':1050})
    assert first['invalidate'] is True
    assert second['accepted'] is False and second['reason']=='debounced'
    assert 'principal' not in first['receipt'] and 'secret' not in first['receipt']


def test_rejects_unacknowledged_notification_type():
    g=SubscriptionGuard()
    g.acknowledge('s1', {'tools':True})
    with pytest.raises(ValueError, match='not acknowledged'):
        g.ingest({'subscription_id':'s1','type':'prompts','event_id':'e2','observed_at_ms':1000})


def test_invalidation_receipt_is_deterministic():
    a=SubscriptionGuard(); b=SubscriptionGuard()
    for g in (a,b): g.acknowledge('s1', {'tools':True})
    x=a.ingest({'subscription_id':'s1','type':'tools','event_id':'e1','observed_at_ms':1000})
    y=b.ingest({'subscription_id':'s1','type':'tools','event_id':'e1','observed_at_ms':1000})
    assert x['receipt']['receipt_hash']==y['receipt']['receipt_hash']
