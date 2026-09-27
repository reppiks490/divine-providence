import pytest
from scripts.quota_probe_guard import normalize_quota, HalfOpenProbeGate

def test_normalize_absolute_and_ratio():
    a=normalize_quota('p', remaining=20, limit=100, reset_at_ms=5000, now_ms=1000)
    assert a['headroom']==0.2 and a['reset_in_ms']==4000
    b=normalize_quota('p', remaining_ratio=0.75, now_ms=1000)
    assert b['headroom']==0.75

def test_malformed_quota_is_conservative_not_negative():
    r=normalize_quota('p', remaining=-5, limit=100, now_ms=0)
    assert r['headroom']==0.0 and r['degraded'] is True

def test_probe_gate_quota_and_deterministic_jitter():
    g=HalfOpenProbeGate(base_interval_ms=1000,max_concurrent=1)
    a=g.decide('alpha',now_ms=10000,quota_headroom=.5,in_flight=0)
    b=g.decide('alpha',now_ms=10000,quota_headroom=.5,in_flight=0)
    assert a==b and 1000 <= a['next_probe_delay_ms'] <= 1250

def test_probe_gate_blocks_low_quota_and_concurrency():
    g=HalfOpenProbeGate(min_headroom=.05,max_concurrent=1)
    assert g.decide('p',0,.01,0)['allowed'] is False
    assert g.decide('p',0,.5,1)['allowed'] is False

def test_receipt_redacts_secrets():
    r=normalize_quota('p',remaining=1,limit=10,now_ms=0,detail={'token':'NOPE'})
    assert 'NOPE' not in str(r)
