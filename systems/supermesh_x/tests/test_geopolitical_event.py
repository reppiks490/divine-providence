import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from geopolitical_event import classify_geopolitical_event, transmission_map


def test_hormuz_event_routes_to_energy_shipping_and_risk_assets():
    event = {
        'text': 'New restrictions on tanker traffic through the Strait of Hormuz amid Iran conflict',
        'actor': 'public_official',
    }
    out = classify_geopolitical_event(event)
    assert 'shipping_chokepoint' in out['themes']
    assert 'iran' in out['themes']
    assert 'energy_supply' in out['channels']
    assert 'shipping' in out['channels']

    tx = transmission_map(out)
    for asset in ['WTI', 'BRENT', 'GOLD', 'DXY', 'VIX', 'VXN', 'NQ', 'ES', 'BTC']:
        assert asset in tx['assets']


def test_sanctions_event_includes_fx_energy_crypto_channels():
    out = classify_geopolitical_event({'text':'U.S. Treasury announces new sanctions targeting Iranian oil and digital asset networks'})
    assert 'sanctions' in out['themes']
    assert 'fx' in out['channels']
    assert 'crypto' in out['channels']
    assert 'energy_supply' in out['channels']
