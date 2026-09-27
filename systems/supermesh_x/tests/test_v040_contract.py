from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]


def test_v040_artifacts_exist():
    required=[
      'scripts/event_study.py','scripts/public_event_impact.py','scripts/recency_weight.py','scripts/geopolitical_event.py',
      'config/market-movers.json','config/trump-market-impact-profile.json',
      'references/current-geopolitical-market-impact.md','workflows/current-market-mover-monitoring.md'
    ]
    missing=[p for p in required if not (ROOT/p).exists()]
    assert not missing, f'missing: {missing}'


def test_manifest_is_v040_and_preserves_v030_baseline():
    text=(ROOT/'manifest.yaml').read_text()
    version=re.search(r'^version:\s*(\d+)\.(\d+)\.(\d+)\s*$', text, re.M)
    assert version and tuple(map(int,version.groups())) >= (0,4,0)
    assert re.search(r'^compatibility_baseline:\s*0\.3\.0\s*$', text, re.M)
    for capability in [
        'market.mover.social_public','market.impact.event_study','market.impact.attribution',
        'market.impact.geopolitical','market.impact.recency','market.impact.cross_asset'
    ]:
        assert capability in text


def test_skill_exposes_current_event_and_social_tracking_policy():
    text=(ROOT/'SKILL.md').read_text().lower()
    assert 'current-geopolitical' in text or 'current geopolitical' in text
    assert 'social' in text
    assert 'public-only' in text or 'public only' in text
    assert 'strait of hormuz' in text
    assert 'iran' in text
