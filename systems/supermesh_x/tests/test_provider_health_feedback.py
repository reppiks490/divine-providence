import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('provider_health_feedback', ROOT/'scripts/provider_health_feedback.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_freshness_and_reconnect_failures_reduce_health_and_rank():
    stable=mod.ProviderHealthFeedback('stable', baseline_health=0.90)
    flaky=mod.ProviderHealthFeedback('flaky', baseline_health=0.90)
    flaky.record('cache_refresh_failed', observed_at_ms=1000)
    flaky.record('subscription_lost', observed_at_ms=1100)
    flaky.record('subscription_lost', observed_at_ms=1200)
    assert flaky.score(now_ms=1200)['health'] < stable.score(now_ms=1200)['health']
    ranked=mod.rank_providers([flaky,stable], now_ms=1200)
    assert [x['provider'] for x in ranked] == ['stable','flaky']

def test_penalties_decay_and_success_recovers_without_exceeding_baseline():
    p=mod.ProviderHealthFeedback('p', baseline_health=0.82, half_life_ms=1000)
    p.record('subscription_lost', observed_at_ms=0)
    low=p.score(now_ms=0)['health']
    later=p.score(now_ms=5000)['health']
    assert low < later <= 0.82
    p.record('success', observed_at_ms=5000)
    assert p.score(now_ms=5000)['health'] <= 0.82

def test_circuit_opens_on_instability_then_half_opens_after_cooldown():
    p=mod.ProviderHealthFeedback('p', baseline_health=0.95, open_threshold=0.60, cooldown_ms=1000)
    for t in (0,1,2,3): p.record('subscription_lost', observed_at_ms=t)
    assert p.score(now_ms=3)['circuit']=='open'
    assert p.score(now_ms=1003)['circuit']=='half_open'
    p.record('success', observed_at_ms=1003)
    assert p.score(now_ms=1003)['circuit']=='closed'

def test_receipt_is_deterministic_and_secret_free():
    p=mod.ProviderHealthFeedback('exa', baseline_health=0.9)
    p.record('cache_refresh_failed', observed_at_ms=10, detail={'api_key':'SECRET','reason':'timeout'})
    a=p.score(now_ms=10); b=p.score(now_ms=10)
    assert a['receipt_hash']==b['receipt_hash']
    assert 'SECRET' not in str(a)
