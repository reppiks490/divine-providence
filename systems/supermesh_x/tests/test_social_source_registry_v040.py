import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_seed_market_movers_expose_public_social_channels():
    reg=json.loads((ROOT/'config'/'market-movers.json').read_text())
    rows={x['id']:x for x in reg['entities']}
    assert 'truth_social' in rows['donald_trump']['public_channels']
    assert 'x' in rows['elon_musk']['public_channels']
    assert reg['policy']['public_only'] is True


def test_social_fallback_policy_exists():
    cfg=json.loads((ROOT/'config'/'social-source-policy.json').read_text())
    assert cfg['public_only'] is True
    assert cfg['fallback_order'][:3] == ['direct_public_source','official_mirror_or_release','reputable_search']
    assert cfg['private_account_access'] is False
