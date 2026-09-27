import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('planner',ROOT/'scripts/source_planner.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_deep_research_has_three_waves():
    p=mod.plan('research','deep')
    assert len(p['source_waves'])==3
    assert 'primary_official' in p['source_waves'][0]['source_classes']

def test_finance_includes_market_capabilities():
    p=mod.plan('finance','standard')
    assert 'market.quote' in p['capabilities']
    assert any('regulatory' in w['source_classes'] for w in p['source_waves'])
