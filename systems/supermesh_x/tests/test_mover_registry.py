import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from mover_registry import default_registry, select_watchlist


def test_registry_contains_trump_musk_and_dynamic_role_buckets():
    reg=default_registry()
    assert 'donald_trump' in reg['entities']
    assert 'elon_musk' in reg['entities']
    assert 'central_bank_leadership' in reg['role_buckets']
    assert 'mega_cap_technology_leadership' in reg['role_buckets']


def test_select_watchlist_filters_by_asset_exposure():
    reg=default_registry()
    watch=select_watchlist(reg,['NQ','TSLA','BTC'])
    ids={x['id'] for x in watch}
    assert 'donald_trump' in ids
    assert 'elon_musk' in ids
