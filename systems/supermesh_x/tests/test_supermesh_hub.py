import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from integration_hub import select_integrations


def test_capability_resolution_uses_connected_and_fallbacks():
    states = {'twelve-data':'ready','interactive-brokers':'auth_required','tickerlayer':'ready'}
    out = select_integrations('market.quote', states)
    assert out['selected'][0]['id'] in {'twelve-data','tickerlayer'}
    assert any(x['id']=='interactive-brokers' for x in out['deferred'])


def test_broker_orders_are_permission_gated():
    out = select_integrations('broker.orders', {'interactive-brokers':'ready'})
    assert out['selected'][0]['permission_class'] == 'read_write_gated'
