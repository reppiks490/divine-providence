from scripts.portfolio_shock_overlay import build_overlay


def test_overlay_maps_holdings_to_observed_shock_without_trading_instruction():
    holdings = [
        {'symbol':'QQQ','weight':0.40,'asset_class':'etf'},
        {'symbol':'XLE','weight':0.10,'asset_class':'etf'},
        {'symbol':'CASH','weight':0.50,'asset_class':'cash'},
    ]
    shocks = {
        'QQQ': {'shock_score': -2.0, 'channel':'equities'},
        'XLE': {'shock_score': 1.5, 'channel':'energy'},
    }
    out = build_overlay(holdings, shocks)
    assert out['gross_exposed_weight'] == 0.5
    assert out['portfolio_shock_score'] == -0.65
    assert out['trade_instruction'] is None
    assert out['causal_claim'] is False
