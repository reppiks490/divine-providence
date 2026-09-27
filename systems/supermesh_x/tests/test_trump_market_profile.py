import json
from pathlib import Path


def test_trump_profile_has_required_sources_and_assets():
    root = Path(__file__).resolve().parents[1]
    profile = json.loads((root / 'config' / 'trump-market-impact-profile.json').read_text())
    assert profile['actor'] == 'Donald Trump'
    assert 'official_primary' in profile['source_classes']
    assert 'reputable_news' in profile['source_classes']
    assert 'NQ' in profile['assets']['equity_index']
    assert 'VIX' in profile['assets']['volatility']
    assert 'DXY' in profile['assets']['fx']
    assert profile['privacy']['private_location_tracking'] is False
