import json
from pathlib import Path


def test_market_mover_registry_covers_social_and_macro_roles():
    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root / 'config' / 'market-movers.json').read_text())
    ids = {e['id'] for e in registry['entities']}
    assert 'donald_trump' in ids
    assert 'elon_musk' in ids
    assert registry['policy']['public_only'] is True
    assert 'social_public' in registry['source_classes']
    assert 'central_bank_leadership' in registry['dynamic_role_buckets']
    assert 'mega_cap_technology_leadership' in registry['dynamic_role_buckets']
    assert 'energy_and_geopolitical_officials' in registry['dynamic_role_buckets']


def test_trump_profile_includes_current_geopolitical_categories():
    root = Path(__file__).resolve().parents[1]
    profile = json.loads((root / 'config' / 'trump-market-impact-profile.json').read_text())
    topics = set(profile['topics'])
    assert {'iran','strait_of_hormuz','sanctions','energy','trade','tariffs','geopolitics'} <= topics
    assert profile['recency']['prefer_current_events'] is True
    assert profile['privacy']['private_location_tracking'] is False
