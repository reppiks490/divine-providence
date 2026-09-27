import pytest
from scripts.subscription_resilience import SubscriptionResilience


def test_lost_stream_requires_refetch_and_new_subscription():
    r=SubscriptionResilience(base_backoff_ms=500,max_backoff_ms=4000)
    out=r.stream_ended('s1', abrupt=True, now_ms=1000)
    assert out['refetch_required'] is True
    assert out['replay_allowed'] is False
    assert out['reuse_subscription_id'] is False
    assert out['retry_after_ms']==1500


def test_backoff_is_bounded_exponential_per_provider():
    r=SubscriptionResilience(base_backoff_ms=100,max_backoff_ms=350)
    assert r.stream_ended('s1', provider='p', now_ms=0)['backoff_ms']==100
    assert r.stream_ended('s2', provider='p', now_ms=0)['backoff_ms']==200
    assert r.stream_ended('s3', provider='p', now_ms=0)['backoff_ms']==350


def test_success_resets_failure_streak():
    r=SubscriptionResilience(base_backoff_ms=100,max_backoff_ms=1000)
    r.stream_ended('s1', provider='p', now_ms=0)
    r.stream_ended('s2', provider='p', now_ms=0)
    r.acknowledged('s3', provider='p')
    assert r.stream_ended('s3', provider='p', now_ms=0)['backoff_ms']==100


def test_stale_event_from_closed_subscription_is_rejected():
    r=SubscriptionResilience()
    r.acknowledged('s1', provider='p')
    r.stream_ended('s1', provider='p', now_ms=10)
    with pytest.raises(ValueError, match='closed subscription'):
        r.accept_event('s1', observed_at_ms=11)


def test_receipt_is_secret_free_and_deterministic():
    a=SubscriptionResilience(); b=SubscriptionResilience()
    x=a.stream_ended('s1', provider='p', now_ms=10, abrupt=True)
    y=b.stream_ended('s1', provider='p', now_ms=10, abrupt=True)
    assert x['receipt_hash']==y['receipt_hash']
    assert 'token' not in x and 'principal' not in x
