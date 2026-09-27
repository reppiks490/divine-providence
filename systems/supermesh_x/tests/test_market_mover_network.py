import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from market_mover_network import build_event_study_plan


def test_network_builds_cross_asset_event_study_with_confounder_lane():
    plan=build_event_study_plan('donald_trump',['NQ','ES','VIX','DXY','TNX'],style='intraday')
    assert plan['entity_id']=='donald_trump'
    assert 'NQ' in plan['assets']
    assert plan['confounder_checks']
    assert plan['counterfactual']['enabled'] is True
    assert plan['attribution_policy']=='association_not_unqualified_causation'
