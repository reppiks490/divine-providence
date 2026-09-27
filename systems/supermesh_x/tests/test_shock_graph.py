from scripts.shock_graph import build_shock_graph


def test_shock_graph_tracks_cross_asset_breadth_and_lag():
    reactions = {
        'CL': {'return_z': 3.2, 'lag_seconds': 20, 'channel':'energy'},
        'GC': {'return_z': 1.7, 'lag_seconds': 45, 'channel':'safe_haven'},
        'NQ': {'return_z': -2.1, 'lag_seconds': 65, 'channel':'equities'},
        'VIX': {'return_z': 2.8, 'lag_seconds': 35, 'channel':'volatility'},
    }
    graph = build_shock_graph(reactions)
    assert graph['breadth'] == 4
    assert graph['peak_asset'] == 'CL'
    assert graph['ordered_assets'][0] == 'CL'
    assert graph['propagation_score'] > 0
