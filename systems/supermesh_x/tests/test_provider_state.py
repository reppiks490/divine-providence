import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('provider_state', ROOT/'scripts/provider_state.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_preflight_required_is_not_ranked_as_ready():
    states={
        'blockscout': {'state':'preflight_required','health':0.95},
        'coingecko': {'state':'ready','health':0.80},
    }
    ranked=mod.rank_candidates(['blockscout','coingecko'], states)
    assert ranked[0]['provider']=='coingecko'
    assert ranked[0]['routable'] is True
    assert ranked[1]['routable'] is False

def test_quota_constrained_provider_is_penalized_but_routable():
    states={
        'a': {'state':'quota_constrained','health':0.95,'quota_remaining_ratio':0.05},
        'b': {'state':'ready','health':0.70},
    }
    ranked=mod.rank_candidates(['a','b'], states)
    assert ranked[0]['provider']=='b'
    assert ranked[1]['provider']=='a'
    assert ranked[1]['routable'] is True
