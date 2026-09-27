import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from ibkr_adapter import connection_plan, authorize_operation


def test_retail_defaults_to_local_gateway_and_read_only():
    p = connection_plan('retail')
    assert p['primary_mode'] == 'client_portal_gateway'
    assert p['market_data'] is True
    assert p['portfolio'] is True
    assert p['orders'] == 'gated'


def test_live_order_requires_explicit_confirmation():
    assert authorize_operation('place_order', explicit_user_confirmation=False)['allowed'] is False
    assert authorize_operation('place_order', explicit_user_confirmation=True)['allowed'] is True
    assert authorize_operation('portfolio_read', explicit_user_confirmation=False)['allowed'] is True
