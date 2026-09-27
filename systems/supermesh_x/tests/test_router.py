import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('router', ROOT/'scripts/capability_router.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_market_route():
    rows=mod.route('market.quote')
    assert rows and rows[0]['provider'] in {'twelve-data','tickerlayer'}

def test_research_route():
    rows=mod.route('research.search')
    names={r['provider'] for r in rows}
    assert 'native-web' in names and 'datablue' in names

def test_availability_filter():
    rows=mod.route('research.search', available=['exa'])
    assert rows and rows[0]['provider']=='exa'
