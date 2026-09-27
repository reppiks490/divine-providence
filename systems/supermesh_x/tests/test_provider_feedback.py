import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from provider_feedback import update_profile, capability_score


def test_feedback_learns_per_capability():
    profile = {}
    profile = update_profile(profile, 'market.quote', ok=True, quality=0.9, latency_ms=100, alpha=0.5)
    profile = update_profile(profile, 'market.quote', ok=False, quality=0.2, latency_ms=1200, alpha=0.5)
    assert profile['market.quote']['samples'] == 2
    assert 0 < capability_score(profile, 'market.quote') < 1
    assert capability_score(profile, 'research.search') == 0.5


def test_feedback_penalizes_failures_and_latency():
    good = {}
    bad = {}
    for _ in range(4):
        good = update_profile(good, 'market.quote', ok=True, quality=0.95, latency_ms=100, alpha=0.5)
        bad = update_profile(bad, 'market.quote', ok=False, quality=0.2, latency_ms=2500, alpha=0.5)
    assert capability_score(good, 'market.quote') > capability_score(bad, 'market.quote')
